import unittest
import os
from queue import Queue
from threading import Event, Lock
from types import SimpleNamespace

from smoothscroll.smoothscroll import SmoothScroll
from smoothscroll.utils.timer import Timer
import smoothscroll.utils.winapi as winapi


class TimerTests(unittest.TestCase):
    def test_clear_accounts_for_every_removed_task(self):
        timer = Timer()
        timer._queue = Queue()
        timer.set_timeout(lambda: None, 60)
        timer.set_timeout(lambda: None, 60)

        timer.clear()
        timer.wait_tasks()

    def test_shutdown_rejects_new_frames_and_has_a_bounded_join(self):
        timer = Timer()
        callback_started = Event()
        release_callback = Event()
        timer.start()
        timer.set_timeout(lambda: (callback_started.set(), release_callback.wait()), 0)
        self.assertTrue(callback_started.wait(1))

        with self.assertRaises(TimeoutError):
            timer.join(timeout=0.01)
        self.assertFalse(timer.set_timeout(lambda: None, 0))
        release_callback.set()
        timer.join(timeout=1)
        self.assertFalse(timer.is_alive())

class ScrollQueueTests(unittest.TestCase):
    def make_scheduler(self, events):
        scheduler = SmoothScroll.__new__(SmoothScroll)
        scheduler._queue = list(events)
        scheduler._queue_lock = Lock()
        scheduler._pending = True
        scheduler._refresh_rate = 0.01
        scheduler._excess_delta_x = 0.4
        scheduler._excess_delta_y = -0.4
        scheduler._pulse = lambda progress, scale: progress
        scheduled = []
        scheduler._schedule_frame = scheduled.append
        return scheduler, scheduled

    def test_finishing_multiple_events_processes_each_event(self):
        from unittest.mock import patch
        import smoothscroll.smoothscroll as module

        def event(value):
            config = SimpleNamespace(duration=1, pulse_scale=1)
            return SimpleNamespace(
                start=0,
                config=config,
                ease=lambda progress, value=value: value * progress,
                previous_delta=0,
                is_horizontal=False,
            )

        scheduler, scheduled = self.make_scheduler([event(120), event(240)])
        emitted = []
        with patch.object(module, "scroll", side_effect=lambda delta, horizontal: emitted.append(delta)):
            scheduler._process_scroll_frame()

        self.assertEqual(emitted, [360])
        self.assertEqual(scheduler._queue, [])
        self.assertEqual(scheduled, [])

    def test_fractional_residue_resets_when_queue_drains(self):
        def event():
            config = SimpleNamespace(duration=1, pulse_scale=1)
            return SimpleNamespace(
                start=0,
                config=config,
                ease=lambda progress: 0,
                previous_delta=0,
                is_horizontal=False,
            )

        scheduler, _ = self.make_scheduler([event()])
        scheduler._process_scroll_frame()

        self.assertEqual(scheduler._excess_delta_x, 0)
        self.assertEqual(scheduler._excess_delta_y, 0)

    def test_event_added_during_frame_is_scheduled_for_next_frame(self):
        from unittest.mock import patch
        import smoothscroll.smoothscroll as module

        def event(start):
            config = SimpleNamespace(duration=1, pulse_scale=1)
            return SimpleNamespace(
                start=start,
                config=config,
                ease=lambda progress: 60 * progress,
                previous_delta=0,
                is_horizontal=False,
            )

        scheduler, scheduled = self.make_scheduler([event(0)])
        inject_once = [True]

        def pulse(progress, _scale):
            if inject_once[0]:
                inject_once[0] = False
                with scheduler._queue_lock:
                    scheduler._queue.append(event(0))
            return progress

        scheduler._pulse = pulse
        with patch.object(module, "scroll"):
            scheduler._process_scroll_frame()

        self.assertEqual(len(scheduler._queue), 1)
        self.assertEqual(scheduled, [scheduler._refresh_rate])


class HookFailureTests(unittest.TestCase):
    def test_hook_install_failure_is_reported_before_ready(self):
        from unittest.mock import patch

        listener = winapi.MouseListener.__new__(winapi.MouseListener)
        listener._ready_event = Event()
        listener._stop_event = Event()
        listener.startup_error = None
        listener.runtime_error = None
        listener._hook = None
        with patch.object(winapi, "LowLevelMouseProc", side_effect=lambda callback: callback), \
             patch.object(winapi.user32, "SetWindowsHookExA", return_value=0), \
             patch.object(winapi, "get_last_error", return_value=5):
            listener.run()

        self.assertTrue(listener._ready_event.is_set())
        self.assertTrue(listener._stop_event.is_set())
        self.assertIsInstance(listener.startup_error, OSError)

    def test_hook_is_uninstalled_when_message_loop_exits(self):
        from unittest.mock import patch

        listener = winapi.MouseListener.__new__(winapi.MouseListener)
        listener._ready_event = Event()
        listener._stop_event = Event()
        listener.startup_error = None
        listener.runtime_error = None
        listener._hook = None
        with patch.object(winapi, "LowLevelMouseProc", side_effect=lambda callback: callback), \
             patch.object(winapi.user32, "SetWindowsHookExA", return_value=123), \
             patch.object(winapi.user32, "PeekMessageW"), \
             patch.object(winapi.user32, "GetMessageW", return_value=0), \
             patch.object(winapi.user32, "UnhookWindowsHookEx", return_value=1) as unhook:
            listener.run()

        unhook.assert_called_once_with(123)
        self.assertTrue(listener._stop_event.is_set())
        self.assertIsNone(listener.runtime_error)

    def test_negative_hook_code_passes_through_without_lookup(self):
        from unittest.mock import patch

        listener = winapi.MouseListener.__new__(winapi.MouseListener)
        l_param = object()
        with patch.object(winapi.user32, "CallNextHookEx", return_value=17) as next_hook, \
             patch.object(winapi, "get_current_app_path") as get_path:
            result = listener._low_level_mouse_handler(-1, winapi.WM_MOUSEWHEEL, l_param)

        self.assertEqual(result, 17)
        get_path.assert_not_called()
        next_hook.assert_called_once()

    def test_process_lookup_failure_returns_unknown_path(self):
        from unittest.mock import patch

        with patch.object(winapi, "GetCursorPos", return_value=(0, 0)), \
             patch.object(winapi, "WindowFromPoint", return_value=1), \
             patch.object(winapi, "GetWindowThreadProcessId", return_value=(1, 42)), \
             patch.object(winapi, "OpenProcess", return_value=None):
            self.assertIsNone(winapi.get_current_app_path())

    def test_callback_failure_preserves_native_wheel(self):
        from unittest.mock import patch
        from smoothscroll.models import AppConfig, SmoothScrollConfig

        listener = winapi.MouseListener.__new__(winapi.MouseListener)
        listener.config = SmoothScrollConfig([
            AppConfig(
                regexp=r'.*', enabled=True,
                scroll_config=SimpleNamespace(inverted=False, horizontal_scroll_key=16)
            )
        ])
        listener._callback = lambda *_args: (_ for _ in ()).throw(RuntimeError("callback failed"))
        wheel = SimpleNamespace(contents=SimpleNamespace(reserved=0, data=120))
        with patch.object(winapi, "get_current_app_path", return_value=r"C:/Apps/example.exe"), \
             patch.object(winapi, "GetAsyncKeyState", return_value=0), \
             patch.object(winapi.user32, "CallNextHookEx", return_value=23) as next_hook:
            result = listener._low_level_mouse_handler(0, winapi.WM_MOUSEWHEEL, wheel)

        self.assertEqual(result, 23)
        next_hook.assert_called_once()


class GuiCallbackTests(unittest.TestCase):
    def test_existing_instance_mutex_is_rejected_and_closed(self):
        from unittest.mock import patch
        from gui import _acquire_instance_mutex

        with patch("gui.win32event.CreateMutex", return_value=123), \
             patch("gui.win32api.GetLastError", return_value=183), \
             patch("gui.win32api.CloseHandle") as close_handle:
            self.assertIsNone(_acquire_instance_mutex())

        close_handle.assert_called_once_with(123)

    def test_tray_actions_are_dispatched_on_the_ui_poll(self):
        from types import SimpleNamespace
        from gui import SmoothScrollGUI

        calls = []
        app = SmoothScrollGUI.__new__(SmoothScrollGUI)
        app._tray_actions = Queue()
        app._closing = True
        app.smooth_scroll = None
        app._queue_tray_action(lambda: calls.append("ran"))
        app.root = SimpleNamespace(after=lambda *_args: self.fail("closed UI must not reschedule"))
        SmoothScrollGUI._process_tray_actions(app)

        self.assertEqual(calls, ["ran"])

    def test_tray_left_activation_defaults_to_open_window(self):
        from gui import SmoothScrollGUI, Lang

        queued = []
        app = SmoothScrollGUI.__new__(SmoothScrollGUI)
        app.lang = Lang("en")
        app._queue_tray_action = queued.append
        app.show_window = lambda: None
        app.toggle_smooth_scroll = lambda: None
        app.quit_app = lambda: None
        menu = SmoothScrollGUI._create_tray_menu(app)

        self.assertTrue(menu.items[0].default)
        menu.items[0](None)
        self.assertIs(queued[0], app.show_window)

    def test_minimize_hides_only_after_window_enters_iconic_state(self):
        from types import SimpleNamespace
        from gui import SmoothScrollGUI

        pending = []
        withdrawn = []
        app = SmoothScrollGUI.__new__(SmoothScrollGUI)
        app.root = SimpleNamespace(
            state=lambda: "iconic",
            after_idle=pending.append,
            withdraw=lambda: withdrawn.append(True),
        )
        SmoothScrollGUI._handle_minimize_to_tray(app)
        self.assertEqual(withdrawn, [])
        pending.pop()()
        self.assertEqual(withdrawn, [True])

        app.root.state = lambda: "withdrawn"
        SmoothScrollGUI._handle_minimize_to_tray(app)
        self.assertEqual(pending, [])

    def test_script_autostart_command_targets_gui_entrypoint(self):
        from unittest.mock import patch
        from gui import SmoothScrollGUI

        with patch("gui.sys.frozen", False, create=True), \
             patch("gui.sys.executable", r"C:\Python\python.exe"), \
             patch("gui.os.path.abspath", side_effect=lambda path: path):
            command = SmoothScrollGUI.application_command(tray=True)

        self.assertEqual(command[0], r"C:\Python\python.exe")
        self.assertTrue(command[1].endswith("main.py"))
        self.assertEqual(command[2], "--tray")

    def test_malformed_config_leaves_default_gui_settings(self):
        from unittest.mock import mock_open, patch
        from gui import SmoothScrollGUI, Lang

        app = SmoothScrollGUI.__new__(SmoothScrollGUI)
        app.lang = Lang("en")
        app.get_default_config = lambda: "defaults"
        with patch("gui.get_app_directory", return_value="C:/app"), \
             patch("gui.os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data="not json")), \
             patch("gui.messagebox.showerror"):
            app.load_config()

        self.assertEqual(app.gui_settings, {})
        self.assertEqual(app.config, "defaults")

    def test_config_save_swaps_runtime_config_without_restarting_service(self):
        import json
        from unittest.mock import Mock, patch
        from tempfile import TemporaryDirectory
        from gui import SmoothScrollGUI

        with TemporaryDirectory() as directory:
            app = SmoothScrollGUI.__new__(SmoothScrollGUI)
            app.save_timer = None
            app.config = object()
            app.lang = SimpleNamespace(get=lambda key: key)
            app.update_global_config = Mock()
            app.serialize_config = lambda: {"apps": []}
            app.smooth_scroll = SimpleNamespace(update_config=Mock())
            with patch("gui.get_app_directory", return_value=directory):
                self.assertTrue(app._write_config())

            with open(os.path.join(directory, "config.json"), encoding="utf-8") as saved:
                self.assertEqual(json.load(saved), {"apps": []})
            app.smooth_scroll.update_config.assert_called_once_with(app.config)

    def test_hover_boundary_includes_descendants_and_excludes_neighbors(self):
        from types import SimpleNamespace
        from gui import _is_widget_within

        row = SimpleNamespace(master=None)
        child = SimpleNamespace(master=row)
        internal_child = SimpleNamespace(master=child)
        neighboring_row = SimpleNamespace(master=None)

        self.assertTrue(_is_widget_within(internal_child, row))
        self.assertFalse(_is_widget_within(neighboring_row, row))
        self.assertFalse(_is_widget_within(None, row))

    def test_invalid_global_value_is_reported_without_escaping_save_callback(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from gui import SmoothScrollGUI

        app = SmoothScrollGUI.__new__(SmoothScrollGUI)
        app.save_timer = "pending"
        app.update_global_config = lambda: (_ for _ in ()).throw(ValueError("invalid value"))
        app.lang = SimpleNamespace(get=lambda key: key)
        with patch("gui.messagebox.showerror") as showerror:
            app._write_config()

        self.assertIsNone(app.save_timer)
        showerror.assert_called_once()

    def test_delete_removes_the_selected_rule_object(self):
        from types import SimpleNamespace
        from gui import SmoothScrollGUI
        from smoothscroll.models import AppConfig

        fallback = AppConfig(regexp=r'.*')
        selected = AppConfig(regexp=r'example\.exe')
        app = SimpleNamespace(
            config=SimpleNamespace(app_configs=(fallback, selected)),
            populate_apps_list=lambda: None,
            auto_save_config=lambda: None,
        )
        SmoothScrollGUI.del_app(app, selected)

        self.assertEqual(app.config.app_configs, (fallback,))

    def test_exception_config_round_trips_with_legacy_enabled_compatibility(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from gui import SmoothScrollGUI, Lang

        app = SmoothScrollGUI.__new__(SmoothScrollGUI)
        legacy = {"apps": [{"regexp": r"example\.exe", "enabled": False}]}
        with patch("gui.ctk.set_appearance_mode"):
            app.config = app.deserialize_config(legacy)

        exception = app.config.app_configs[1]
        self.assertFalse(exception.exception_active)
        app.appearance_var = SimpleNamespace(get=lambda: "System")
        app.start_minimized_var = SimpleNamespace(get=lambda: False)
        app.lang = Lang("en")
        app.gui_settings = {}
        app.root = SimpleNamespace(state=lambda: "normal", geometry=lambda: "500x700+120+80")
        saved = app.serialize_config()
        self.assertFalse(saved["apps"][1]["exception_active"])
        self.assertNotIn("enabled", saved["apps"][1])
        self.assertEqual(saved["gui_settings"]["window_geometry"], "500x700+120+80")

    def test_saved_window_geometry_is_restored_and_configure_is_debounced(self):
        from types import SimpleNamespace
        from gui import SmoothScrollGUI

        applied = []
        app = SmoothScrollGUI.__new__(SmoothScrollGUI)
        app.gui_settings = {"window_geometry": "640x720+120+80"}
        app.root = SimpleNamespace(
            geometry=lambda value=None: applied.append(value) if value else "640x720+120+80",
            state=lambda: "normal",
        )
        app.appearance_var = SimpleNamespace(set=lambda _value: None)
        app.language_var = SimpleNamespace(set=lambda _value: None)
        app.start_minimized_var = SimpleNamespace(set=lambda _value: None)
        app.lang = SimpleNamespace(lang="en")
        app.config = SimpleNamespace(app_configs=[])
        app.start_minimized = False
        app.auto_save_config = lambda: applied.append("save")

        SmoothScrollGUI.update_gui_from_config(app)
        SmoothScrollGUI._handle_window_configure(
            app, SimpleNamespace(widget=app.root)
        )

        self.assertEqual(applied, ["640x720+120+80", "save"])
        self.assertEqual(app.gui_settings["window_geometry"], "640x720+120+80")


if __name__ == "__main__":
    unittest.main()
