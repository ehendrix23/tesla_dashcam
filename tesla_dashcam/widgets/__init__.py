"""Graphical overlay widgets for Tesla dashcam telemetry display."""

from .base import Widget, OverlayCanvas, WidgetTheme, THEME_PRESETS
from .steering_wheel import SteeringWheelWidget
from .turn_signals import TurnSignalWidget
from .brake_indicator import BrakeIndicatorWidget
from .accel_gauge import AccelGaugeWidget
from .speed_display import SpeedDisplayWidget
from .gear_indicator import GearIndicatorWidget
from .location_display import LocationDisplayWidget
from .datetime_display import DateTimeDisplayWidget
from .autopilot_indicator import AutopilotIndicatorWidget
from .gforce_display import GForceDisplayWidget
from .compass_display import CompassDisplayWidget
from .center_cluster import CenterClusterWidget
from .elevation_display import ElevationDisplayWidget

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
    "DateTimeDisplayWidget",
    "AutopilotIndicatorWidget",
    "GForceDisplayWidget",
    "CompassDisplayWidget",
    "CenterClusterWidget",
    "ElevationDisplayWidget",
]
