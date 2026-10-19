from ctypes import WinDLL, byref, c_int, get_last_error
from ctypes.wintypes import MSG
from threading import Thread, Event
from typing import Callable

from win32api import GetAsyncKeyState, mouse_event, OpenProcess, CloseHandle, EnumDisplaySettings, SetConsoleCtrlHandler
from win32con import WH_MOUSE_LL, WM_MOUSEWHEEL, WM_QUIT, MOUSEEVENTF_HWHEEL, MOUSEEVENTF_WHEEL, MAXIMUM_ALLOWED
from win32gui import GetCursorPos, WindowFromPoint
from win32process import GetWindowThreadProcessId, GetModuleFileNameEx

from ..models import SmoothScrollConfig, LowLevelMouseProc

user32 = WinDLL('user32', use_last_error=True)


def resolve_scroll_config(app_configs, current_app_path):
    """Resolve the effective rule without applying any Windows side effects."""
    if not current_app_path:
        return None
    current_app_path = current_app_path.replace('\\', '/').casefold()
    app_configs = tuple(app_configs)
    global_config = next(
        (app_config for app_config in reversed(app_configs)
         if app_config.regexp and app_config.regexp.pattern == '.*'),
        None
    )
    special_config = None
    has_special_rule = False

    for app_config in app_configs:
        is_global = bool(app_config.regexp and app_config.regexp.pattern == '.*')
        match = current_app_path == app_config.path.casefold() or bool(
            app_config.regexp and app_config.regexp.search(current_app_path)
        )
        if not match:
            continue
        if is_global:
            continue

        has_special_rule = True
        # A matching disabled custom rule is an explicit opt-out.
        # Custom entries are disable exceptions. An active exception blocks
        # scrolling; disabling the exception restores global fallback.
        special_config = None if app_config.exception_active else (
            global_config.scroll_config
            if global_config and global_config.enabled
            else None
        )

    if has_special_rule:
        return special_config
    return global_config.scroll_config if global_config and global_config.enabled else None


class MouseListener(Thread):
    def __init__(self, callback: Callable, config: SmoothScrollConfig, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self._callback = callback
        self.config = config

        self._stop_event = Event()
        self._ready_event = Event()
        self.startup_error = None
        self.runtime_error = None
        self._hook = None

    def run(self):
        try:
            mouse_callback = LowLevelMouseProc(self._low_level_mouse_handler)
            self._hook = user32.SetWindowsHookExA(
                WH_MOUSE_LL,
                mouse_callback,
                c_int(0),
                c_int(0)
            )
            if not self._hook:
                error = get_last_error()
                raise OSError(error, "SetWindowsHookExA failed")

            msg = MSG()
            # Create this thread's message queue before reporting startup ready.
            user32.PeekMessageW(byref(msg), None, 0, 0, 0)
            self._ready_event.set()
            while bRet := user32.GetMessageW(msg, c_int(0), c_int(0), c_int(0)):
                if bRet == -1:
                    error = get_last_error()
                    raise OSError(error, "GetMessageW failed")
                user32.TranslateMessage(msg)
                user32.DispatchMessageA(msg)
        except Exception as exc:
            if not self._ready_event.is_set():
                self.startup_error = exc
            else:
                self.runtime_error = exc
        finally:
            self._ready_event.set()
            if self._hook:
                try:
                    if not user32.UnhookWindowsHookEx(self._hook):
                        self.runtime_error = OSError(get_last_error(), "UnhookWindowsHookEx failed")
                except Exception as exc:
                    self.runtime_error = exc
                self._hook = None
            self._stop_event.set()

    def _low_level_mouse_handler(self, n_code, w_param, l_param):
        if n_code < 0:
            return user32.CallNextHookEx(c_int(0), n_code, w_param, l_param)
        if w_param == WM_MOUSEWHEEL:
            if not l_param.contents.reserved:
                try:
                    current_app_path = get_current_app_path()
                    scroll_config = resolve_scroll_config(self.config.app_configs, current_app_path)
                    if scroll_config:
                        self._callback(
                            l_param.contents.data / (2 << 15) * (-1 if scroll_config.inverted else 1),
                            bool(GetAsyncKeyState(scroll_config.horizontal_scroll_key)),
                            scroll_config
                        )
                        return 1  # to prevent processing by the system
                except Exception:
                    # Preserve native scrolling if lookup or callback fails.
                    pass
        return user32.CallNextHookEx(c_int(0), n_code, w_param, l_param)

    def listen(self) -> None:
        self._stop_event.wait()

    def wait_until_ready(self, timeout: float) -> bool:
        return self._ready_event.wait(timeout)

    def quit(self) -> None:
        if self.ident is None or not self.is_alive():
            return
        if not user32.PostThreadMessageW(self.native_id, WM_QUIT, c_int(0), c_int(0)):
            error = get_last_error()
            raise OSError(error, "PostThreadMessageW(WM_QUIT) failed")

    def join(self, timeout=None):
        if self.ident is None:
            return
        self.quit()
        super().join(timeout=5 if timeout is None else timeout)
        if self.is_alive():
            raise TimeoutError("Mouse hook thread did not stop")


def scroll(delta: int, is_horizontal: bool = False) -> None:
    mouse_event(MOUSEEVENTF_HWHEEL if is_horizontal else MOUSEEVENTF_WHEEL, 0, 0, delta, 0)


def get_current_app_path() -> str | None:
    h_process = None
    try:
        cursor_pos = GetCursorPos()
        active_hwnd = WindowFromPoint(cursor_pos)
        _, pid = GetWindowThreadProcessId(active_hwnd)
        if not pid:
            return None
        h_process = OpenProcess(MAXIMUM_ALLOWED, 0, pid)
        if not h_process:
            return None
        current_app_path = GetModuleFileNameEx(h_process, None)
        return current_app_path.replace('\\', r'/') if current_app_path else None
    except Exception:
        return None
    finally:
        if h_process:
            try:
                CloseHandle(h_process)
            except Exception:
                pass


def get_display_frequency() -> int:
    return EnumDisplaySettings(None, -1).DisplayFrequency


def set_console_ctrl_handler(callback: Callable) -> None:
    SetConsoleCtrlHandler(callback, True)
