import json
import customtkinter as ctk
from tkinter import filedialog, messagebox, TclError
from typing import Optional
import easing_functions
import pystray
from PIL import Image, ImageDraw, ImageTk
import threading
import winreg
import os
import sys
import subprocess
import webbrowser
import tempfile
from queue import Empty, Queue
import win32api
import win32event


def get_app_directory():
    """ Get the application directory (where the app is installed) """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        return os.path.dirname(sys.executable)
    else:
        # Running as Python script
        return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = get_app_directory()

    return os.path.join(base_path, relative_path)


def _is_widget_within(widget, ancestor):
    while widget is not None and widget is not ancestor:
        widget = getattr(widget, "master", None)
    return widget is ancestor


def _acquire_instance_mutex():
    mutex = win32event.CreateMutex(None, True, r"Local\SmoothScrollForWindowsGUI")
    if win32api.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        win32api.CloseHandle(mutex)
        return None
    return mutex


def _release_instance_mutex(mutex):
    if mutex:
        try:
            win32event.ReleaseMutex(mutex)
        finally:
            win32api.CloseHandle(mutex)

from smoothscroll import SmoothScroll, SmoothScrollConfig, AppConfig, ScrollConfig
from win32con import VK_SHIFT, VK_CONTROL, VK_MENU

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class Lang:
    def __init__(self, lang='en'):
        self.lang = lang
        self.texts = {
            'en': {
                'title': 'SmoothScroll GUI',
                'global_settings': 'Global Settings',
                'apps': 'Applications (exceptions)',
                'app_settings': 'App Settings',
                'save': 'Save',
                'start': 'Start',
                'stop': 'Stop',
                'appearance_mode': 'Appearance Mode',
                'language': 'Language',
                'autostart': 'Autostart with Windows',
                'start_minimized': 'Start minimized to tray',
                'distance': 'Distance (px, None for auto):',
                'acceleration': 'Acceleration:',
                'opposite_acceleration': 'Opposite Acceleration:',
                'acceleration_delta': 'Acceleration Delta (ms):',
                'acceleration_max': 'Acceleration Max:',
                'duration': 'Duration (ms):',
                'pulse_scale': 'Pulse Scale:',
                'inverted': 'Inverted',
                'easing_function': 'Easing Function:',
                'horizontal_scroll_key': 'Horizontal Scroll Key:',
                'add': 'Add',
                'remove': 'Remove',
                'edit': 'Edit',
                'path': 'Path:',
                'regexp': 'Regexp:',
                'enabled': 'Enabled',
                'scroll_enabled': 'Smooth scrolling',
                'save_btn': 'Save',
                'success': 'Success',
                'error': 'Error',
                'warning': 'Warning',
                'config_saved': 'Config saved to',
                'smoothscroll_started': 'SmoothScroll started',
                'smoothscroll_stopped': 'SmoothScroll stopped',
                'already_running': 'Already running',
                'not_running': 'Not running',
                'autostart_enabled': 'Autostart enabled',
                'autostart_disabled': 'Autostart disabled',
                'appearance_applied': 'Appearance changes applied.',
                'restart_for_lang': 'Restart the application to apply language changes. Dont forget press "Save" button.',
                'select_app': 'Select an application to',
                'add_app': 'Add Application',
                'edit_app': 'Edit Application',
                'load_config_error': 'Error loading config',
                'config_load_success': 'Config loaded successfully',
                'info': 'Information',
                'about_title': 'About',
                'about_desc': 'This application provides smooth scrolling in all applications (except exceptions in settings) on Windows, with many settings, and most importantly - a graphical interface.',
                'about_fork': 'This application is a fork of the',
                'about_original': 'Smoothscroll-for-windows',
                'about_improvements': 'project by re1von, main improvements - GUI.',
                'about_link': 'Project link:',
                'about_project_url': 'https://github.com/vadenko/Smoothscroll-for-windows-GUI',
                'about_version': 'Version: 1.0.2',
                'tray_open': 'Open',
                'tray_quit': 'Quit',
                'error_already_running': 'Application is already running.',
                'app_list_path': 'Path',
                'app_list_regexp': 'Regexp',
                'app_list_enabled': 'Enabled'
            },
            'ru': {
                'title': 'SmoothScroll GUI',
                'global_settings': 'Глобальные настройки',
                'apps': 'Приложения (исключения)',
                'app_settings': 'Настройки приложения',
                'save': 'Сохранить',
                'start': 'Запустить',
                'stop': 'Остановить',
                'appearance_mode': 'Режим внешнего вида',
                'language': 'Язык',
                'autostart': 'Автозагрузка с Windows',
                'start_minimized': 'Запускать свернутым',
                'distance': 'Расстояние (px, None для авто):',
                'acceleration': 'Ускорение:',
                'opposite_acceleration': 'Обратное ускорение:',
                'acceleration_delta': 'Дельта ускорения (мс):',
                'acceleration_max': 'Максимальное ускорение:',
                'duration': 'Длительность (мс):',
                'pulse_scale': 'Масштаб импульса:',
                'inverted': 'Инвертировано',
                'easing_function': 'Функция easing:',
                'horizontal_scroll_key': 'Клавиша горизонтальной прокрутки:',
                'add': 'Добавить',
                'remove': 'Удалить',
                'edit': 'Редактировать',
                'path': 'Путь:',
                'regexp': 'Регулярное выражение:',
                'enabled': 'Включено',
                'scroll_enabled': 'Плавная прокрутка',
                'save_btn': 'Сохранить',
                'success': 'Успех',
                'error': 'Ошибка',
                'warning': 'Предупреждение',
                'config_saved': 'Конфиг сохранен в',
                'smoothscroll_started': 'SmoothScroll запущен',
                'smoothscroll_stopped': 'SmoothScroll остановлен',
                'already_running': 'Уже запущено',
                'not_running': 'Не запущено',
                'autostart_enabled': 'Автозагрузка включена',
                'autostart_disabled': 'Автозагрузка отключена',
                'appearance_applied': 'Изменения режима внешнего вида применены.',
                'restart_for_lang': 'Перезапустите приложение для применения изменений языка. Не забудьте нажать кнопку "Сохранить"',
                'select_app': 'Выберите приложение для',
                'add_app': 'Добавить приложение',
                'edit_app': 'Редактировать приложение',
                'load_config_error': 'Ошибка загрузки конфига',
                'config_load_success': 'Конфиг загружен успешно',
                'info': 'Информация',
                'about_title': 'О приложении',
                'about_desc': 'Это приложение для придания плавной прокрутки во всех приложениях (кроме исключений в настройках) в Windows, имеет множество настроек, и самое главное - графический интерфейс.',
                'about_fork': 'Это приложение является форком проекта',
                'about_original': 'Smoothscroll-for-windows',
                'about_improvements': 'от re1von, основные улучшения - GUI.',
                'about_link': 'Ссылка на проект:',
                'about_project_url': 'https://github.com/vadenko/Smoothscroll-for-windows-GUI',
                'about_version': 'Версия: 1.0.2',
                'tray_open': 'Открыть',
                'tray_quit': 'Закрыть',
                'error_already_running': 'Приложение уже запущено',
                'app_list_path': 'Путь',
                'app_list_regexp': 'Рег.выр',
                'app_list_enabled': 'Вкл'
            },
            'zh': {
                'title': 'SmoothScroll GUI',
                'global_settings': '全局设置',
                'apps': '应用程序（例外）',
                'app_settings': '应用设置',
                'save': '保存',
                'start': '启动',
                'stop': '停止',
                'appearance_mode': '外观模式',
                'language': '语言',
                'autostart': '开机自启',
                'start_minimized': '启动时最小化到托盘',
                'distance': '滚动距离（像素，None为自动）：',
                'acceleration': '加速度：',
                'opposite_acceleration': '反向加速度：',
                'acceleration_delta': '加速度增量（毫秒）：',
                'acceleration_max': '最大加速度：',
                'duration': '滚动时长（毫秒）：',
                'pulse_scale': '脉冲缩放：',
                'inverted': '反转滚动方向',
                'easing_function': '缓动函数：',
                'horizontal_scroll_key': '横向滚动快捷键：',
                'add': '添加',
                'remove': '删除',
                'edit': '编辑',
                'path': '程序路径：',
                'regexp': '正则匹配规则：',
                'enabled': '启用',
                'scroll_enabled': '平滑滚动',
                'save_btn': '保存',
                'success': '操作成功',
                'error': '错误',
                'warning': '警告',
                'config_saved': '配置已保存到：',
                'smoothscroll_started': '平滑滚动已启动',
                'smoothscroll_stopped': '平滑滚动已停止',
                'already_running': '平滑滚动已在运行中',
                'not_running': '平滑滚动未运行',
                'autostart_enabled': '开机自启已开启',
                'autostart_disabled': '开机自启已关闭',
                'appearance_applied': '外观设置已生效。',
                'restart_for_lang': '切换语言需要重启程序生效。',
                'select_app': '请选择要',
                'add_app': '添加应用',
                'edit_app': '编辑应用',
                'load_config_error': '加载配置失败',
                'config_load_success': '配置加载成功',
                'info': '提示',
                'about_title': '关于',
                'about_desc': '本应用为Windows全系统提供平滑鼠标滚轮效果，可在例外设置中排除指定应用，提供丰富参数调节，且自带图形配置界面。',
                'about_fork': '本应用是',
                'about_original': 'Smoothscroll-for-windows',
                'about_improvements': '项目的分支版本，主要改进为新增图形GUI界面。',
                'about_link': '项目地址：',
                'about_project_url': 'https://github.com/vadenko/Smoothscroll-for-windows-GUI',
                'about_version': '版本：1.0.2',
                'tray_open': '打开主窗口',
                'tray_quit': '退出',
                'error_already_running': '应用已在运行中',
                'app_list_path': '路径',
                'app_list_regexp': '正则',
                'app_list_enabled': '已启用'
            }
        }

    def get(self, key):
        return self.texts[self.lang].get(key, key)

class SmoothScrollGUI:
    def __init__(self, root, auto_start=False, start_minimized=False):
        self.lang = Lang('en')
        # Check for single instance
        self.instance_mutex = _acquire_instance_mutex()
        if not self.instance_mutex:
            messagebox.showerror(self.lang.get('error'), self.lang.get('error_already_running'))
            sys.exit(1)

        self.root = root
        self.root.title("SmoothScroll for Windows GUI")
        self.root.geometry("500x700")
        try:
            self.root.iconbitmap(resource_path('icon.ico'))
            self.root.iconphoto(True, ImageTk.PhotoImage(Image.open(resource_path('icon.png'))))
        except:
            pass  # Icon not found, use default

        self.smooth_scroll: Optional[SmoothScroll] = None
        self.config = self.get_default_config()
        self.auto_start = auto_start
        self.start_minimized = start_minimized
        self.lang = Lang('en')  # Default language
        self.save_timer = None
        self._app_picker_window = None
        self._tray_actions = Queue()
        self._tray_poll_id = None
        self._closing = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_config()  # Load config first to set language
        self.create_tray_icon()
        self.create_widgets()
        self.populate_apps_list()  # Populate after widgets are created
        self.update_gui_from_config()  # Update GUI after widgets are created
        self._tray_poll_id = self.root.after(50, self._process_tray_actions)

        if self.auto_start:
            self.start_smooth_scroll()
        if self.start_minimized:
            self.on_close()

    def get_default_config(self):
        return SmoothScrollConfig(
            app_config=[
                AppConfig(
                    regexp=r'.*',
                    scroll_config=ScrollConfig(
                        distance=None,
                        acceleration=1.,
                        opposite_acceleration=1.2,
                        acceleration_delta=70,
                        acceleration_max=14,
                        duration=200,
                        pulse_scale=3,
                        ease=easing_functions.LinearInOut,
                        inverted=False,
                        horizontal_scroll_key=VK_SHIFT
                    ),
                ),
            ]
        )

    def create_widgets(self):
        # Tabview for tabs
        self.tabview = ctk.CTkTabview(self.root, width=880, height=600)
        self.tabview.pack(pady=20, padx=20, fill="both", expand=True)

        # Global settings tab
        self.tabview.add(self.lang.get('global_settings'))
        self.global_frame = self.tabview.tab(self.lang.get('global_settings'))
        self.create_global_settings()

        # Apps tab
        self.tabview.add(self.lang.get('apps'))
        self.apps_frame = self.tabview.tab(self.lang.get('apps'))
        self.create_apps_settings()

        # App settings tab
        self.tabview.add(self.lang.get('app_settings'))
        self.app_settings_frame = self.tabview.tab(self.lang.get('app_settings'))
        self.create_app_settings()

        # About tab
        self.tabview.add(self.lang.get('about_title'))
        self.about_frame = self.tabview.tab(self.lang.get('about_title'))
        self.create_about_tab()

        # Control buttons
        self.control_frame = ctk.CTkFrame(self.root)
        self.control_frame.pack(fill="x", pady=10, padx=20)

        self.toggle_btn = ctk.CTkButton(self.control_frame, text=self.lang.get('start'), command=self.toggle_smooth_scroll, fg_color="#2E7D32", hover_color="#1B5E20")
        self.toggle_btn.pack(side="right", padx=5)

    def create_global_settings(self):
        # Assuming global config is the first AppConfig with regexp .*
        global_config = self.config.app_configs[0].scroll_config

        # Use pack with frames for better layout
        frame = ctk.CTkScrollableFrame(self.global_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text=self.lang.get('distance')).pack(anchor="w", pady=2)
        self.distance_var = ctk.StringVar(value=str(global_config.distance))
        ctk.CTkEntry(frame, textvariable=self.distance_var).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('acceleration')).pack(anchor="w", pady=2)
        self.acceleration_var = ctk.DoubleVar(value=global_config.acceleration)
        ctk.CTkEntry(frame, textvariable=self.acceleration_var).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('opposite_acceleration')).pack(anchor="w", pady=2)
        self.opposite_acceleration_var = ctk.DoubleVar(value=global_config.opposite_acceleration)
        ctk.CTkEntry(frame, textvariable=self.opposite_acceleration_var).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('acceleration_delta')).pack(anchor="w", pady=2)
        self.acceleration_delta_var = ctk.IntVar(value=int(global_config.acceleration_delta * 1000))
        ctk.CTkEntry(frame, textvariable=self.acceleration_delta_var).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('acceleration_max')).pack(anchor="w", pady=2)
        self.acceleration_max_var = ctk.DoubleVar(value=global_config.acceleration_max)
        ctk.CTkEntry(frame, textvariable=self.acceleration_max_var).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('duration')).pack(anchor="w", pady=2)
        self.duration_var = ctk.IntVar(value=int(global_config.duration * 1000))
        ctk.CTkEntry(frame, textvariable=self.duration_var).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('pulse_scale')).pack(anchor="w", pady=2)
        self.pulse_scale_var = ctk.DoubleVar(value=global_config.pulse_scale)
        ctk.CTkEntry(frame, textvariable=self.pulse_scale_var).pack(fill="x", pady=2)

        self.inverted_var = ctk.BooleanVar(value=global_config.inverted)
        ctk.CTkCheckBox(frame, text=self.lang.get('inverted'), variable=self.inverted_var).pack(anchor="w", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('easing_function')).pack(anchor="w", pady=2)
        ease_options = ["LinearInOut", "QuadraticEaseInOut", "CubicEaseInOut", "QuarticEaseInOut", "QuinticEaseInOut"]
        self.ease_var = ctk.StringVar(value=global_config.ease.__name__ if hasattr(global_config.ease, '__name__') else "LinearInOut")
        ctk.CTkOptionMenu(frame, variable=self.ease_var, values=ease_options).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('horizontal_scroll_key')).pack(anchor="w", pady=2)
        key_options = ["VK_SHIFT", "VK_CONTROL", "VK_MENU"]
        current_key = {VK_SHIFT: "VK_SHIFT", VK_CONTROL: "VK_CONTROL", VK_MENU: "VK_MENU"}.get(global_config.horizontal_scroll_key, "VK_SHIFT")
        self.horizontal_key_var = ctk.StringVar(value=current_key)
        ctk.CTkOptionMenu(frame, variable=self.horizontal_key_var, values=key_options).pack(fill="x", pady=2)

        # 绑定所有参数自动保存
        for var in [self.distance_var, self.acceleration_var, self.opposite_acceleration_var,
                    self.acceleration_delta_var, self.acceleration_max_var, self.duration_var,
                    self.pulse_scale_var, self.inverted_var, self.ease_var, self.horizontal_key_var]:
            var.trace_add("write", self.auto_save_config)

        # Remove autostart from global settings

    def get_visible_window_exes(self):
        import win32gui
        import win32process
        exes = set()
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    name = psutil.Process(pid).name().replace('.exe', '')
                    exes.add(name)
                except:
                    pass
        win32gui.EnumWindows(cb, None)
        return sorted(list(exes))

    def create_apps_settings(self):
        self.apps_scrollable = ctk.CTkScrollableFrame(self.apps_frame, scrollbar_button_color="#242424", scrollbar_button_hover_color="#3a3a3a")
        self.apps_scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        self.populate_apps_list()

    def populate_apps_list(self):
        for w in self.apps_scrollable.winfo_children():
            w.destroy()
        for i, app in enumerate(self.config.app_configs):
            is_global = app.regexp and app.regexp.pattern == '.*'
            if is_global:
                continue
            row = ctk.CTkFrame(self.apps_scrollable, fg_color="transparent", corner_radius=4)
            row.pack(fill="x", pady=3, padx=2)
            if not is_global:
                delete_button = ctk.CTkButton(
                    row,
                    text="删除",
                    width=58,
                    height=28,
                    corner_radius=4,
                    fg_color="#8B2E2E",
                    hover_color="#B83A3A",
                    text_color="#FFFFFF",
                    command=lambda target=app: self.del_app(target),
                )
                delete_button.pack(side="right", padx=(4, 6), pady=2)
            enable_var = ctk.BooleanVar(value=not app.exception_active)
            def toggle(target=app, var=enable_var):
                target.exception_active = not var.get()
                self.auto_save_config()
                # 立刻热重载，不用点总开关
                if self.smooth_scroll:
                    self.stop_smooth_scroll()
                    self.start_smooth_scroll()
            ctk.CTkSwitch(
                row,
                text=self.lang.get('scroll_enabled'),
                width=32,
                variable=enable_var,
                command=toggle
            ).pack(side="right", padx=6)
            if is_global:
                ctk.CTkLabel(row, text="全局默认", anchor="w", font=ctk.CTkFont(size=14)).pack(side="left", padx=10, pady=8, fill="x", expand=True)
            else:
                current = app.regexp.pattern.replace('.exe', '') if app.regexp else "未选择程序"
                lbl = ctk.CTkLabel(row, text=current, anchor="w", font=ctk.CTkFont(size=14))
                lbl.pack(side="left", padx=10, pady=8, fill="x", expand=True)
                # hover提示：鼠标移到行任意位置都变明显浅灰，离开变回透明
                def on_enter(e, r=row):
                    r.configure(fg_color="#3a3a3a")
                def on_leave(e, r=row):
                    def clear_if_outside():
                        current = self.root.winfo_containing(
                            self.root.winfo_pointerx(), self.root.winfo_pointery()
                        )
                        if not _is_widget_within(current, r):
                            r.configure(fg_color="transparent")
                    r.after_idle(clear_if_outside)
                def bind_hover(w):
                    # Append to existing widget bindings. Replacing them
                    # breaks CustomTkinter button and switch interactions.
                    w.bind("<Enter>", on_enter, add="+")
                    w.bind("<Leave>", on_leave, add="+")
                    for child in w.winfo_children():
                        bind_hover(child)
                bind_hover(row)
                def open_pick(target=app):
                    import re
                    if self._app_picker_window is not None:
                        try:
                            if self._app_picker_window.winfo_exists():
                                self._app_picker_window.lift()
                                self._app_picker_window.focus_force()
                                return
                        except TclError:
                            self._app_picker_window = None
                    win = ctk.CTkToplevel(self.root)
                    self._app_picker_window = win
                    win.title("更换程序")
                    # 弹窗居中打开
                    w,h = 260,350
                    self.root.update_idletasks()
                    x = self.root.winfo_x() + (self.root.winfo_width() - w)//2
                    y = self.root.winfo_y() + (self.root.winfo_height() - h)//2
                    win.geometry(f"{w}x{h}+{x}+{y}")
                    win.attributes("-topmost", True)
                    def close_picker():
                        if self._app_picker_window is win:
                            self._app_picker_window = None
                        win.destroy()
                    win.protocol("WM_DELETE_WINDOW", close_picker)
                    scroll = ctk.CTkScrollableFrame(win)
                    scroll.pack(fill="both", expand=True, padx=5, pady=5)
                    # 打开弹窗重新枚举最新窗口
                    windows = self.get_visible_window_exes()
                    # 已存在的规则，排除当前条目本身
                    existing = set()
                    for existing_rule in self.config.app_configs:
                        if existing_rule is not target and existing_rule.regexp and existing_rule.regexp.pattern != '.*':
                            existing.add(existing_rule.regexp.pattern)
                    def change_rule(name):
                        target.regexp = re.compile(re.escape(name) + r'\.exe')
                        self.auto_save_config()
                        self.populate_apps_list()
                        close_picker()
                    for w_name in windows:
                        if re.escape(w_name) + r'\.exe' in existing:
                            ctk.CTkButton(scroll, text=w_name+"（已存在）", fg_color="gray25", state="disabled").pack(fill="x", pady=1)
                        else:
                            ctk.CTkButton(scroll, text=w_name, fg_color="transparent", command=lambda name=w_name: change_rule(name)).pack(fill="x", pady=1)
                lbl.bind("<Button-1>", lambda e, pick=open_pick: pick())
        ctk.CTkButton(self.apps_scrollable, text="+ 添加禁用例外", fg_color="transparent", command=self.new_app, anchor="w").pack(fill="x", pady=6, padx=2)

    def del_app(self, target):
        # Delete by the rule object rendered in this row. The global rule is
        # hidden from the list, so a visual row number is not a stable index.
        self.config.app_configs = tuple(
            app for app in self.config.app_configs if app is not target
        )
        self.populate_apps_list()
        self.auto_save_config()

    def new_app(self):
        import re
        if self._app_picker_window is not None:
            try:
                if self._app_picker_window.winfo_exists():
                    self._app_picker_window.lift()
                    self._app_picker_window.focus_force()
                    return
            except TclError:
                self._app_picker_window = None
        win = ctk.CTkToplevel(self.root)
        self._app_picker_window = win
        win.title("选择要添加的程序")
        w,h = 260,350
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - w)//2
        y = self.root.winfo_y() + (self.root.winfo_height() - h)//2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.attributes("-topmost", True)
        def close_picker():
            if self._app_picker_window is win:
                self._app_picker_window = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", close_picker)
        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        # 打开弹窗时重新枚举最新窗口列表
        windows = self.get_visible_window_exes()
        # 已存在的规则程序名
        existing = set()
        for app in self.config.app_configs:
            if app.regexp and app.regexp.pattern != '.*':
                existing.add(app.regexp.pattern)
        def add_rule(name):
            self.config.app_configs = self.config.app_configs + (
                AppConfig(path=None, regexp=re.compile(re.escape(name) + r'\.exe'), enabled=True),
            )
            self.auto_save_config()
            self.populate_apps_list()
            close_picker()
        for w_name in windows:
            if re.escape(w_name) + r'\.exe' in existing:
                # 已存在的程序，按钮灰掉，不可点
                ctk.CTkButton(scroll, text=w_name+"（已存在）", fg_color="gray25", state="disabled").pack(fill="x", pady=1)
            else:
                ctk.CTkButton(scroll, text=w_name, fg_color="transparent", command=lambda name=w_name: add_rule(name)).pack(fill="x", pady=1)

    def create_app_settings(self):
        frame = ctk.CTkScrollableFrame(self.app_settings_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text=self.lang.get('appearance_mode')).pack(anchor="w", pady=2)
        appearance_options = ["System", "Light", "Dark"]
        self.appearance_var = ctk.StringVar(value="System")
        ctk.CTkOptionMenu(frame, variable=self.appearance_var, values=appearance_options, command=self.change_appearance_mode).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text=self.lang.get('language')).pack(anchor="w", pady=2)
        self.language_var = ctk.StringVar(value="en")
        ctk.CTkOptionMenu(frame, variable=self.language_var, values=["en", "ru", "zh"], command=self.change_language).pack(fill="x", pady=2)

        ctk.CTkLabel(frame, text="").pack(pady=5)  # Spacer
        ctk.CTkLabel(frame, text=self.lang.get('app_settings')).pack(anchor="w", pady=5, padx=10)
        self.autostart_var = ctk.BooleanVar(value=self.is_autostart_enabled())
        ctk.CTkCheckBox(frame, text=self.lang.get('autostart'), variable=self.autostart_var, command=self.toggle_autostart).pack(anchor="w", pady=2)
        
        self.start_minimized_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text=self.lang.get('start_minimized'), variable=self.start_minimized_var).pack(anchor="w", pady=2)

        # 绑定设置项自动保存
        for var in [self.appearance_var, self.language_var, self.autostart_var, self.start_minimized_var]:
            var.trace_add("write", self.auto_save_config)

    def change_appearance_mode(self, mode):
        ctk.set_appearance_mode(mode)

    def change_language(self, lang):
        if lang == self.lang.lang:
            return
        self.lang.lang = lang
        self.auto_save_config()
        if messagebox.askyesno(self.lang.get('info'), self.lang.get('restart_for_lang') + '\n\n是否立即重启？'):
            if self.save_timer:
                self.root.after_cancel(self.save_timer)
                self.save_timer = None
            if not self._write_config():
                return
            if self.quit_app():
                subprocess.Popen(self.application_command())

    @staticmethod
    def application_command(tray=False):
        args = ["--tray"] if tray else []
        if getattr(sys, 'frozen', False):
            return [os.path.abspath(sys.executable), *args]
        entrypoint = os.path.join(get_app_directory(), "main.py")
        return [sys.executable, entrypoint, *args]

    def change_color_theme(self, theme):
        if theme == "red":
            ctk.set_default_color_theme("red.json")
        else:
            ctk.set_default_color_theme(theme)
        messagebox.showinfo(self.lang.get('info'), self.lang.get('appearance_applied'))

    def load_config(self):
        self.gui_settings = {}
        config_path = os.path.join(get_app_directory(), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                gui_settings = data.get("gui_settings", {})
                lang = gui_settings.get("language", "en")
                self.lang = Lang(lang)
                self.config = self.deserialize_config(data)
                self.gui_settings = gui_settings
            except Exception as e:
                messagebox.showerror(self.lang.get('load_config_error'), str(e))
                self.config = self.get_default_config()
        else:
            # Use default config
            self.gui_settings = {}
            pass

    def update_global_config(self):
        global_config = self.config.app_configs[0].scroll_config
        global_config.distance = None if self.distance_var.get() == "None" else float(self.distance_var.get())
        global_config.acceleration = self.acceleration_var.get()
        global_config.opposite_acceleration = self.opposite_acceleration_var.get()
        global_config.acceleration_delta = self.acceleration_delta_var.get() / 1000
        global_config.acceleration_max = self.acceleration_max_var.get()
        global_config.duration = self.duration_var.get() / 1000
        global_config.pulse_scale = self.pulse_scale_var.get()
        global_config.inverted = self.inverted_var.get()

        # Update ease
        ease_name = self.ease_var.get()
        global_config.ease = getattr(easing_functions, ease_name, easing_functions.LinearInOut)

        # Update horizontal key
        key_name = self.horizontal_key_var.get()
        global_config.horizontal_scroll_key = {"VK_SHIFT": VK_SHIFT, "VK_CONTROL": VK_CONTROL, "VK_MENU": VK_MENU}.get(key_name, VK_SHIFT)

    def auto_save_config(self, *args):
        # 防抖：取消之前的定时器，500ms后再写入
        if self.save_timer:
            self.root.after_cancel(self.save_timer)
        self.save_timer = self.root.after(500, self._write_config)

    def _write_config(self):
        try:
            self.update_global_config()
            config_path = os.path.join(get_app_directory(), "config.json")
            data = self.serialize_config()
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', dir=os.path.dirname(config_path),
                    prefix='.config-', suffix='.tmp', delete=False
                ) as config_file:
                    temp_path = config_file.name
                    json.dump(data, config_file, indent=4)
                    config_file.flush()
                    os.fsync(config_file.fileno())
                os.replace(temp_path, config_path)
                temp_path = None
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            # Swap the config snapshot without restarting the global hook.
            if self.smooth_scroll:
                self.smooth_scroll.update_config(self.config)
            return True
        except Exception as e:
            messagebox.showerror(self.lang.get('error'), str(e))
            return False
        finally:
            self.save_timer = None

    def serialize_config(self):
        data = {
            "apps": [],
            "gui_settings": {
                "appearance_mode": self.appearance_var.get(),
                "language": self.lang.lang,
                "start_minimized": self.start_minimized_var.get()
            }
        }
        for app in self.config.app_configs:
            app_data = {
                "path": app.path,
                "regexp": app.regexp.pattern if app.regexp else None
            }
            if app.regexp and app.regexp.pattern == '.*':
                app_data["enabled"] = app.enabled
            else:
                app_data["exception_active"] = app.exception_active
            if app.scroll_config:
                app_data["scroll_config"] = {
                    "distance": app.scroll_config.distance,
                    "acceleration": app.scroll_config.acceleration,
                    "opposite_acceleration": app.scroll_config.opposite_acceleration,
                    "acceleration_delta": app.scroll_config.acceleration_delta,
                    "acceleration_max": app.scroll_config.acceleration_max,
                    "duration": app.scroll_config.duration,
                    "pulse_scale": app.scroll_config.pulse_scale,
                    "ease": app.scroll_config.ease.__name__ if hasattr(app.scroll_config.ease, '__name__') else "LinearInOut",
                    "inverted": app.scroll_config.inverted,
                    "horizontal_scroll_key": app.scroll_config.horizontal_scroll_key
                }
            data["apps"].append(app_data)
        return data

    def deserialize_config(self, data):
        apps = []
        raw_apps = data.get("apps", [])
        if not isinstance(raw_apps, list):
            raise ValueError("配置中的 apps 必须是数组")
        for app_data in raw_apps:
            if not isinstance(app_data, dict):
                raise ValueError("配置中的规则必须是对象")
            scroll_config = None
            if "scroll_config" in app_data:
                sc = app_data["scroll_config"]
                ease_name = sc.get("ease", "LinearInOut")
                ease = getattr(easing_functions, ease_name, easing_functions.LinearInOut)
                scroll_config = ScrollConfig(
                    distance=sc.get("distance"),
                    acceleration=sc.get("acceleration", 1.0),
                    opposite_acceleration=sc.get("opposite_acceleration", 1.2),
                    acceleration_delta=int(sc.get("acceleration_delta", 0.07) * 1000),
                    acceleration_max=sc.get("acceleration_max", 14.0),
                    duration=int(sc.get("duration", 0.2) * 1000),
                    pulse_scale=sc.get("pulse_scale", 3.0),
                    ease=ease,
                    inverted=sc.get("inverted", False),
                    horizontal_scroll_key=sc.get("horizontal_scroll_key", VK_SHIFT)
                )
            app = AppConfig(
                path=app_data.get("path"),
                regexp=app_data.get("regexp"),
                enabled=app_data.get("enabled", True),
                scroll_config=scroll_config,
                exception_active=app_data.get("exception_active", app_data.get("enabled", True))
            )
            apps.append(app)

        # The global rule is an internal fallback and must always exist. Keep
        # its enabled flag when the user explicitly disabled it, while filling
        # missing parameters from the built-in defaults.
        default_global = self.get_default_config().app_configs[0]
        global_index = next(
            (i for i, app in enumerate(apps)
             if app.regexp and app.regexp.pattern == '.*'),
            None
        )
        if global_index is None:
            apps.insert(0, default_global)
        else:
            global_config = apps[global_index]
            if global_config.scroll_config is None:
                global_config.scroll_config = default_global.scroll_config
            if global_index != 0:
                apps.insert(0, apps.pop(global_index))

        # Apply GUI settings
        gui_settings = data.get("gui_settings", {})
        appearance_mode = gui_settings.get("appearance_mode", "System")
        ctk.set_appearance_mode(appearance_mode)

        return SmoothScrollConfig(app_config=apps)

    def update_gui_from_config(self):
        if self.config.app_configs:
            global_config = self.config.app_configs[0].scroll_config
            self.distance_var.set(str(global_config.distance))
            self.acceleration_var.set(global_config.acceleration)
            self.opposite_acceleration_var.set(global_config.opposite_acceleration)
            self.acceleration_delta_var.set(int(global_config.acceleration_delta * 1000))
            self.acceleration_max_var.set(global_config.acceleration_max)
            self.duration_var.set(int(global_config.duration * 1000))
            self.pulse_scale_var.set(global_config.pulse_scale)
            self.inverted_var.set(global_config.inverted)

            # Update ease
            self.ease_var.set(global_config.ease.__name__ if hasattr(global_config.ease, '__name__') else "LinearInOut")

            # Update horizontal key
            current_key = {VK_SHIFT: "VK_SHIFT", VK_CONTROL: "VK_CONTROL", VK_MENU: "VK_MENU"}.get(global_config.horizontal_scroll_key, "VK_SHIFT")
            self.horizontal_key_var.set(current_key)

        # Update GUI settings
        self.appearance_var.set(self.gui_settings.get("appearance_mode", "System"))
        self.language_var.set(self.lang.lang)
        self.start_minimized_var.set(self.gui_settings.get("start_minimized", False))
        
        # Apply start_minimized from config if not explicitly set via command line
        if self.gui_settings.get("start_minimized", False) and not self.start_minimized:
            self.start_minimized = True
            self.auto_start = True  # Also auto-start SmoothScroll
            self.root.after(100, self.on_close)

    def toggle_smooth_scroll(self):
        if self.smooth_scroll:
            self.stop_smooth_scroll()
        else:
            self.start_smooth_scroll()

    def start_smooth_scroll(self):
        if self.smooth_scroll:
            return True
        self.update_global_config()
        runtime = SmoothScroll(self.config)
        try:
            runtime.start(is_block=False)
        except Exception as e:
            self.smooth_scroll = None
            messagebox.showerror(self.lang.get('error'), str(e))
            return False
        self.smooth_scroll = runtime
        # 更新按钮状态：运行中
        self.toggle_btn.configure(text=self.lang.get('stop'), fg_color="#C62828", hover_color="#8E0000")
        return True

    def stop_smooth_scroll(self):
        if self.smooth_scroll:
            try:
                self.smooth_scroll.join()
            except Exception as e:
                messagebox.showerror(self.lang.get('error'), str(e))
                return False
            self.smooth_scroll = None
        # 更新按钮状态：已停止
        self.toggle_btn.configure(text=self.lang.get('start'), fg_color="#2E7D32", hover_color="#1B5E20")
        return True

    def create_tray_icon(self):
        # Load icon from file, or create default if not found
        try:
            image = Image.open(resource_path('icon.png'))
        except FileNotFoundError:
            # Create a simple icon if file not found
            image = Image.new('RGB', (64, 64), color='blue')
            draw = ImageDraw.Draw(image)
            draw.ellipse((16, 16, 48, 48), fill='white')

        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem(self.lang.get('tray_open'), lambda _icon, _item: self._queue_tray_action(self.show_window)),
            pystray.MenuItem(lambda _item: self.lang.get('stop') if self.smooth_scroll else self.lang.get('start'), lambda _icon, _item: self._queue_tray_action(self.toggle_smooth_scroll)),
            pystray.MenuItem(self.lang.get('tray_quit'), lambda _icon, _item: self._queue_tray_action(self.quit_app))
        )

        self.tray_icon = pystray.Icon("SmoothScroll", image, "SmoothScroll", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _queue_tray_action(self, action):
        self._tray_actions.put(action)

    def _process_tray_actions(self):
        while True:
            try:
                action = self._tray_actions.get_nowait()
            except Empty:
                break
            try:
                action()
            except Exception as e:
                messagebox.showerror(self.lang.get('error'), str(e))
        runtime = self.smooth_scroll
        if runtime and not runtime.is_running():
            error = runtime.get_runtime_error()
            try:
                runtime.join()
            except Exception as e:
                error = error or e
            self.smooth_scroll = None
            self.toggle_btn.configure(
                text=self.lang.get('start'),
                fg_color="#2E7D32",
                hover_color="#1B5E20",
            )
            if error:
                messagebox.showerror(self.lang.get('error'), str(error))
        if not self._closing:
            self._tray_poll_id = self.root.after(50, self._process_tray_actions)

    def on_close(self):
        self.root.withdraw()  # Hide window instead of closing

    def show_window(self):
        self.root.deiconify()  # Show window
        self.root.lift()  # Bring to front

    def quit_app(self):
        if self.smooth_scroll:
            try:
                self.smooth_scroll.join()
            except Exception as e:
                messagebox.showerror(self.lang.get('error'), str(e))
                return False
        self._closing = True
        if self._tray_poll_id:
            self.root.after_cancel(self._tray_poll_id)
            self._tray_poll_id = None
        self.tray_icon.stop()
        _release_instance_mutex(self.instance_mutex)
        self.instance_mutex = None
        self.root.quit()
        return True

    def is_autostart_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "SmoothScroll")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False

    def toggle_autostart(self):
        if self.autostart_var.get():
            self.enable_autostart()
        else:
            self.disable_autostart()

    def enable_autostart(self):
        try:
            command = self.application_command(tray=True)
            if not getattr(sys, 'frozen', False):
                python_exe = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
                command[0] = python_exe
            exe_path = subprocess.list2cmdline(command)
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "SmoothScroll", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            messagebox.showinfo(self.lang.get('success'), self.lang.get('autostart_enabled'))
        except Exception as e:
            messagebox.showerror(self.lang.get('error'), str(e))
            self.autostart_var.set(False)

    def disable_autostart(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "SmoothScroll")
            winreg.CloseKey(key)
            messagebox.showinfo(self.lang.get('success'), self.lang.get('autostart_disabled'))
        except FileNotFoundError:
            pass  # Already disabled
        except Exception as e:
            messagebox.showerror(self.lang.get('error'), str(e))
            self.autostart_var.set(True)

    def open_link(self, url):
        webbrowser.open(url)

    def create_about_tab(self):
        frame = ctk.CTkScrollableFrame(self.about_frame)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text=self.lang.get('about_title'), font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=5)
        ctk.CTkLabel(frame, text=self.lang.get('about_desc'), wraplength=800, justify="left").pack(anchor="w", pady=10)
        ctk.CTkLabel(frame, text=self.lang.get('about_fork')).pack(anchor="w")
        link1 = ctk.CTkLabel(frame, text=self.lang.get('about_original'), cursor="hand2", text_color="blue", font=ctk.CTkFont(underline=True))
        link1.pack(anchor="w")
        link1.bind("<Button-1>", lambda e: self.open_link("https://github.com/re1von/Smoothscroll-for-windows"))
        ctk.CTkLabel(frame, text=self.lang.get('about_improvements')).pack(anchor="w")
        ctk.CTkLabel(frame, text=self.lang.get('about_link')).pack(anchor="w", pady=(10,0))
        link2 = ctk.CTkLabel(frame, text=self.lang.get('about_project_url'), cursor="hand2", text_color="blue", font=ctk.CTkFont(underline=True))
        link2.pack(anchor="w")
        link2.bind("<Button-1>", lambda e: self.open_link("https://github.com/vadenko"))
        ctk.CTkLabel(frame, text=self.lang.get('about_version')).pack(anchor="w", pady=(5,0))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tray", action="store_true")
    args = parser.parse_args()
    root = ctk.CTk()
    app = SmoothScrollGUI(root, auto_start=args.tray, start_minimized=args.tray)
    root.mainloop()
