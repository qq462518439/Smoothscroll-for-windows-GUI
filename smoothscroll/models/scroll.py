import re
from time import perf_counter
from typing import Optional, Union, Type, Literal, Iterable

from win32con import VK_SHIFT, VK_CONTROL, VK_MENU

from . import EasingFunction


class ScrollConfig:
    def __init__(
            self,
            distance: Optional[Union[int, float]],
            acceleration: Union[int, float],
            opposite_acceleration: Union[int, float],
            acceleration_delta: Union[int, float],
            acceleration_max: Union[int, float],
            duration: Union[int, float],
            pulse_scale: Union[int, float],
            ease: Type[EasingFunction],
            inverted: bool,
            horizontal_scroll_key: Optional[Literal[VK_SHIFT, VK_CONTROL, VK_MENU]] = None
    ):
        self.distance = distance
        self.acceleration = acceleration
        self.opposite_acceleration = opposite_acceleration
        self.acceleration_delta = acceleration_delta / 1000
        self.acceleration_max = acceleration_max
        self.duration = duration / 1000
        self.pulse_scale = pulse_scale
        self.ease = ease
        self.inverted = inverted
        self.horizontal_scroll_key = horizontal_scroll_key


class AppConfig:
    def __init__(
            self,
            path: Optional[str] = None,
            regexp: Optional[str] = None,
            enabled: Optional[bool] = True,
            scroll_config: Optional[ScrollConfig] = None,
            exception_active: Optional[bool] = None,
    ):
        self.path = (path or '').replace('\\', r'/').casefold()
        if isinstance(regexp, re.Pattern):
            self.regexp = re.compile(regexp.pattern, regexp.flags | re.IGNORECASE)
        else:
            self.regexp = re.compile(regexp or r'<>', re.IGNORECASE)
        self.enabled = bool(enabled)
        # `enabled` remains the legacy config field; custom rules use the
        # explicit exception state from the current schema.
        self.exception_active = bool(
            enabled if exception_active is None else exception_active
        )
        # Keep the parameters even when a rule is disabled.  The enabled flag
        # controls matching; retaining the config lets the GUI edit and save a
        # disabled global rule without losing its settings.
        self.scroll_config = scroll_config


class SmoothScrollConfig:
    def __init__(self, app_config: Union[Iterable[AppConfig], AppConfig]):
        self.app_configs = tuple(app_config) if isinstance(app_config, Iterable) else (app_config,)


class ScrollEvent:
    def __init__(self, delta: int | float, is_horizontal: bool, config):
        self.is_horizontal = is_horizontal
        self.ease = config.ease(end=delta)
        self.config = config

        self.previous_delta = .0
        self.start = perf_counter()
