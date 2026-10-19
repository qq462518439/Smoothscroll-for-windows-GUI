import unittest
from queue import Queue
from threading import Lock
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
        saved = app.serialize_config()
        self.assertFalse(saved["apps"][1]["exception_active"])
        self.assertNotIn("enabled", saved["apps"][1])


if __name__ == "__main__":
    unittest.main()
