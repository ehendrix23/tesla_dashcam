"""
Graphical telemetry overlay generator.

Renders Pillow-based graphical widgets (steering wheel, gauges, indicators)
from SEI telemetry data. Produces PNG frames and an FFmpeg concat demuxer file
for compositing onto the dashcam video.
"""

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from PIL import Image

try:
    from .sei_extractor import SeiFrame
except ImportError:
    from sei_extractor import SeiFrame

from .widgets.base import OverlayCanvas, WidgetTheme, THEME_PRESETS
from .widgets.steering_wheel import SteeringWheelWidget
from .widgets.turn_signals import TurnSignalWidget
from .widgets.brake_indicator import BrakeIndicatorWidget
from .widgets.accel_gauge import AccelGaugeWidget
from .widgets.speed_display import SpeedDisplayWidget
from .widgets.gear_indicator import GearIndicatorWidget
from .widgets.location_display import LocationDisplayWidget
from .widgets.datetime_display import DateTimeDisplayWidget
from .widgets.autopilot_indicator import AutopilotIndicatorWidget
from .widgets.gforce_display import GForceDisplayWidget
from .widgets.compass_display import CompassDisplayWidget
from .widgets.center_cluster import CenterClusterWidget
from .widgets.elevation_display import ElevationDisplayWidget

_LOGGER = logging.getLogger(__name__)

DEFAULT_FRAME_RATE = 36.0

# Height scale factors per size preset (relative to "medium" = 1.0)
_HEIGHT_SCALE = {"small": 0.75, "medium": 1.0, "large": 1.35}

# Classic layout presets (backward compat)
_CLASSIC_PRESETS = {
    "small": {"steering": 100, "font_scale": 0.9, "gauge_w": 32, "gauge_h": 90},
    "medium": {"steering": 140, "font_scale": 1.2, "gauge_w": 40, "gauge_h": 120},
    "large": {"steering": 190, "font_scale": 1.6, "gauge_w": 52, "gauge_h": 160},
}

ALL_WIDGETS = [
    "steering", "turn", "brake", "accel", "speed", "gear",
    "location", "datetime", "autopilot", "gforce", "compass", "cluster",
    "elevation",
]


@dataclass
class GraphicalOverlaySettings:
    """Configuration for graphical telemetry overlay."""

    position: str = "bottom-left"
    size_preset: str = "medium"
    widgets: List[str] = field(default_factory=lambda: ["all"])
    theme_name: str = "default"
    speed_unit: str = "mph"
    font_path: Optional[str] = None
    frame_rate: float = DEFAULT_FRAME_RATE
    margin_x: int = 30
    margin_y: int = 15
    start_time: Optional[datetime] = None
    layout_name: str = "dashboard"


def _resolve_widgets(widget_list: List[str]) -> List[str]:
    """Resolve 'all' keyword and validate widget names."""
    if "all" in widget_list:
        return list(ALL_WIDGETS)
    valid = [w for w in widget_list if w in ALL_WIDGETS]
    return valid if valid else list(ALL_WIDGETS)


def _build_dashboard_layout(
    settings: GraphicalOverlaySettings,
    video_width: int,
    video_height: int,
) -> OverlayCanvas:
    """Build the dashboard-style top layout.

    All telemetry widgets arranged in a horizontal bar across the top:
    [DateTime] [Speed+AP] [Cluster: Steering+Gauges+GForce] [Gear+Turn] [Compass]

    Fully proportional layout that adapts to any video width (1280, 1920, etc).
    """
    theme = THEME_PRESETS.get(settings.theme_name, THEME_PRESETS["default"])
    enabled = _resolve_widgets(settings.widgets)
    font = settings.font_path

    # Proportional margins based on video size
    mx = max(8, video_width // 100)
    my = max(8, video_height // 80)
    usable_w = video_width - 2 * mx

    # Bar height: ~21% of video height, scaled by size preset
    hs = _HEIGHT_SCALE.get(settings.size_preset, 1.0)
    bar_h = int(video_height * 0.21 * hs)
    gap = max(6, int(usable_w * 0.006))

    widgets = []

    # === Proportional widget sizes (fractions of usable width) ===
    datetime_w = int(usable_w * 0.175)
    datetime_h = int(bar_h * 0.52)

    speed_w = int(usable_w * 0.125)
    speed_h = int(bar_h * 0.88)

    cluster_w = int(usable_w * 0.155)
    cluster_h = bar_h
    steer_sz = int(bar_h * 0.48)
    gw = max(18, int(cluster_w * 0.15))
    gh = int(bar_h * 0.36)

    gear_w = int(usable_w * 0.08)
    gear_h = int(bar_h * 0.27)
    turn_w = int(usable_w * 0.065)
    turn_h = int(bar_h * 0.19)

    compass_w = int(usable_w * 0.195)
    compass_h = int(bar_h * 0.52)

    # === Position widgets ===

    # Elevation indicator dimensions (placed below datetime or compass)
    elev_h = int(bar_h * 0.30)

    # DateTime at top left
    if "datetime" in enabled:
        widgets.append(DateTimeDisplayWidget(
            mx, my, datetime_w, datetime_h, theme,
            start_time=settings.start_time,
            frame_rate=settings.frame_rate,
            font_path=font,
        ))

    # Compass at top right
    if "compass" in enabled:
        cx = video_width - compass_w - mx
        widgets.append(CompassDisplayWidget(
            cx, my, compass_w, compass_h, theme, font_path=font,
        ))

    # Elevation below compass
    if "elevation" in enabled:
        elev_y = my + compass_h + 4
        elev_w = compass_w
        ex = video_width - elev_w - mx
        widgets.append(ElevationDisplayWidget(
            ex, elev_y, elev_w, elev_h, theme, font_path=font,
        ))

    # Center group: [Speed+AP] [Cluster] [Gear+Turn]
    # Positioned in the space between datetime and compass
    left_edge = mx + datetime_w + gap
    right_edge = video_width - mx - compass_w - gap
    gear_block_w = max(gear_w, turn_w)
    total_center = speed_w + gap + cluster_w + gap + gear_block_w
    center_start = left_edge + (right_edge - left_edge - total_center) // 2
    center_start = max(left_edge, center_start)

    # Speed + autopilot badge
    if "speed" in enabled:
        show_ap = "autopilot" in enabled
        widgets.append(SpeedDisplayWidget(
            center_start, my, speed_w, speed_h, theme,
            speed_unit=settings.speed_unit,
            show_autopilot=show_ap,
            font_path=font,
        ))

    # Center cluster (steering + angle + ACC/BRK + G-force)
    if "cluster" in enabled:
        ccx = center_start + speed_w + gap
        widgets.append(CenterClusterWidget(
            ccx, my, cluster_w, cluster_h, theme,
            steering_size=steer_sz, gauge_w=gw, gauge_h=gh,
            font_path=font,
        ))

    # Gear indicator + turn signals (stacked vertically)
    gear_x = center_start + speed_w + gap + cluster_w + gap
    if "gear" in enabled:
        widgets.append(GearIndicatorWidget(
            gear_x, my, gear_w, gear_h, theme, font_path=font,
        ))

    if "turn" in enabled:
        widgets.append(TurnSignalWidget(
            gear_x, my + gear_h + 4, turn_w, turn_h, theme,
        ))

    return OverlayCanvas(video_width, video_height, widgets)


def _build_classic_layout(
    settings: GraphicalOverlaySettings,
    video_width: int,
    video_height: int,
) -> OverlayCanvas:
    """Build the classic overlay layout (backward compat).

    Speed at top-center, steering at bottom-center with ACC/BRK flanking,
    location at bottom-left, datetime at top-right.
    """
    theme = THEME_PRESETS.get(settings.theme_name, THEME_PRESETS["default"])
    size = _CLASSIC_PRESETS.get(settings.size_preset, _CLASSIC_PRESETS["medium"])
    enabled = _resolve_widgets(settings.widgets)

    steer_size = size["steering"]
    scale = size["font_scale"]
    gauge_w = size["gauge_w"]
    gauge_h = size["gauge_h"]

    mx = settings.margin_x
    my = settings.margin_y

    widgets = []
    font = settings.font_path

    top_y = my

    if "datetime" in enabled:
        dw = int(280 * scale)
        dh = int(30 * scale)
        dx = video_width - dw - mx
        widgets.append(DateTimeDisplayWidget(
            dx, top_y, dw, dh, theme,
            start_time=settings.start_time,
            frame_rate=settings.frame_rate,
            font_path=font,
        ))

    if "speed" in enabled:
        sw = int(140 * scale)
        sh = int(90 * scale)
        sx = (video_width - sw) // 2
        widgets.append(SpeedDisplayWidget(
            sx, top_y, sw, sh, theme,
            speed_unit=settings.speed_unit, font_path=font,
        ))

    if "gear" in enabled:
        gw = int(120 * scale)
        gh = int(34 * scale)
        gx = (video_width + int(140 * scale)) // 2 + 10
        widgets.append(GearIndicatorWidget(
            gx, top_y + 6, gw, gh, theme, font_path=font,
        ))

    if "turn" in enabled:
        tw = int(90 * scale)
        th = int(30 * scale)
        turn_x = (video_width + int(140 * scale)) // 2 + 10
        turn_y = top_y + int(42 * scale)
        widgets.append(TurnSignalWidget(
            turn_x, turn_y, tw, th, theme,
        ))

    steer_y = video_height - steer_size - my - int(20 * scale)
    steer_x = (video_width - steer_size) // 2

    if "steering" in enabled:
        widgets.append(SteeringWheelWidget(
            steer_x, steer_y, steer_size, steer_size, theme,
            font_path=font,
        ))

    if "accel" in enabled:
        ax = steer_x - gauge_w - 14
        ay = steer_y + (steer_size - gauge_h) // 2
        widgets.append(AccelGaugeWidget(
            ax, ay, gauge_w, gauge_h, theme, font_path=font,
        ))

    if "brake" in enabled:
        bx = steer_x + steer_size + 14
        by = steer_y + (steer_size - gauge_h) // 2
        widgets.append(BrakeIndicatorWidget(
            bx, by, gauge_w, gauge_h, theme, font_path=font,
        ))

    if "location" in enabled:
        lw = int(300 * scale)
        lh = int(44 * scale)
        lx = mx
        ly = video_height - lh - my
        widgets.append(LocationDisplayWidget(
            lx, ly, lw, lh, theme, font_path=font,
        ))

    if "compass" in enabled:
        cw = int(230 * scale)
        ch = int(60 * scale)
        cx = video_width - cw - mx
        cy = video_height - ch - my
        widgets.append(CompassDisplayWidget(
            cx, cy, cw, ch, theme, font_path=font,
        ))

    return OverlayCanvas(video_width, video_height, widgets)


def _build_widget_layout(
    settings: GraphicalOverlaySettings,
    video_width: int,
    video_height: int,
) -> OverlayCanvas:
    """Build the widget layout based on the layout_name setting."""
    if settings.layout_name == "classic":
        return _build_classic_layout(settings, video_width, video_height)
    return _build_dashboard_layout(settings, video_width, video_height)


def generate_graphical_overlay(
    frames: List[SeiFrame],
    settings: Optional[GraphicalOverlaySettings] = None,
    output_dir: Optional[str] = None,
    video_width: int = 1920,
    video_height: int = 960,
) -> Optional[str]:
    """Generate overlay PNG frames and FFmpeg concat demuxer file.

    Args:
        frames: List of SeiFrame objects with telemetry data.
        settings: Overlay configuration. Uses defaults if None.
        output_dir: Directory for PNG output. Creates temp dir if None.
        video_width: Video width for positioning.
        video_height: Video height for positioning.

    Returns:
        Path to the FFmpeg concat demuxer file, or None if no frames.
    """
    if not frames:
        _LOGGER.debug("No frames provided for graphical overlay")
        return None

    if settings is None:
        settings = GraphicalOverlaySettings()

    canvas = _build_widget_layout(settings, video_width, video_height)
    frame_duration = 1.0 / settings.frame_rate

    # Create output directory
    created_dir = False
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tesla_gfx_overlay_")
        created_dir = True
    elif not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        created_dir = True

    # Render unique states and build concat file
    state_cache: Dict[tuple, str] = {}
    concat_entries = []
    state_counter = 0

    last_key = None
    last_count = 0

    for frame in frames:
        key = canvas.composite_state_key(frame)

        if key == last_key:
            last_count += 1
            continue

        # Flush previous run
        if last_key is not None:
            png_path = state_cache[last_key]
            concat_entries.append((png_path, last_count * frame_duration))

        # Render new state if not cached
        if key not in state_cache:
            img = canvas.render(frame)
            png_name = f"overlay_{state_counter:06d}.png"
            png_path = os.path.join(output_dir, png_name)
            img.save(png_path, "PNG")
            state_cache[key] = png_path
            state_counter += 1

        last_key = key
        last_count = 1

    # Flush final run
    if last_key is not None:
        png_path = state_cache[last_key]
        concat_entries.append((png_path, last_count * frame_duration))

    if not concat_entries:
        if created_dir:
            shutil.rmtree(output_dir, ignore_errors=True)
        return None

    # Write concat demuxer file
    concat_path = os.path.join(output_dir, "overlay_concat.txt")
    with open(concat_path, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for png_path, duration in concat_entries:
            rel = os.path.basename(png_path)
            f.write(f"file {rel}\n")
            f.write(f"duration {duration:.6f}\n")
        if concat_entries:
            f.write(f"file {os.path.basename(concat_entries[-1][0])}\n")

    _LOGGER.info(
        "Generated graphical overlay: %d unique states, %d frames, dir=%s",
        state_counter, len(frames), output_dir,
    )

    return concat_path


def cleanup_overlay_dir(concat_path: str) -> None:
    """Remove the temporary overlay directory and all its contents."""
    if concat_path:
        overlay_dir = os.path.dirname(concat_path)
        if overlay_dir and os.path.isdir(overlay_dir):
            shutil.rmtree(overlay_dir, ignore_errors=True)
            _LOGGER.debug("Cleaned up overlay dir: %s", overlay_dir)
