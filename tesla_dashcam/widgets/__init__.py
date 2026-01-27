"""Graphical overlay widgets for Tesla dashcam telemetry display."""

from .base import Widget, OverlayCanvas, WidgetTheme, THEME_PRESETS
from .steering_wheel import SteeringWheelWidget
from .turn_signals import TurnSignalWidget
from .brake_indicator import BrakeIndicatorWidget
from .accel_gauge import AccelGaugeWidget
from .speed_display import SpeedDisplayWidget
from .gear_indicator import GearIndicatorWidget
from .location_display import LocationDisplayWidget

__all__ = [
    "Widget",
    "OverlayCanvas",
    "WidgetTheme",
    "THEME_PRESETS",
    "SteeringWheelWidget",
    "TurnSignalWidget",
    "BrakeIndicatorWidget",
    "AccelGaugeWidget",
    "SpeedDisplayWidget",
    "GearIndicatorWidget",
    "LocationDisplayWidget",
]
