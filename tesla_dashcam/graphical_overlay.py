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

_LOGGER = logging.getLogger(__name__)

DEFAULT_FRAME_RATE = 36.0

# Widget cluster dimensions per size preset
_SIZE_PRESETS = {
    "small": {"steering": 100, "font_scale": 0.9, "gauge_w": 32, "gauge_h": 90},
    "medium": {"steering": 140, "font_scale": 1.2, "gauge_w": 40, "gauge_h": 120},
    "large": {"steering": 190, "font_scale": 1.6, "gauge_w": 52, "gauge_h": 160},
}

ALL_WIDGETS = [
    "steering", "turn", "brake", "accel", "speed", "gear", "location", "datetime",
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
    margin_y: int = 25
    start_time: Optional[datetime] = None


def _resolve_widgets(widget_list: List[str]) -> List[str]:
    """Resolve 'all' keyword and validate widget names."""
    if "all" in widget_list:
        return list(ALL_WIDGETS)
    valid = [w for w in widget_list if w in ALL_WIDGETS]
    return valid if valid else list(ALL_WIDGETS)


def _build_widget_layout(
    settings: GraphicalOverlaySettings,
    video_width: int,
    video_height: int,
) -> OverlayCanvas:
    """Create widget instances positioned within the overlay canvas.

    Layout inspired by TeslaClip:
    - Top right: Date/time
    - Top center: Speed + Gear + Turn signals
    - Bottom center: Steering wheel with ACC/BRK vertical gauges on sides
    - Bottom left: Location/heading
    """
    theme = THEME_PRESETS.get(settings.theme_name, THEME_PRESETS["default"])
    size = _SIZE_PRESETS.get(settings.size_preset, _SIZE_PRESETS["medium"])
    enabled = _resolve_widgets(settings.widgets)

    steer_size = size["steering"]
    scale = size["font_scale"]
    gauge_w = size["gauge_w"]
    gauge_h = size["gauge_h"]

    mx = settings.margin_x
    my = settings.margin_y

    widgets = []
    font = settings.font_path

    # === TOP ROW: Date/time (right), Speed (center), Gear + Turn signals ===
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
        # Place gear to the right of speed
        gx = (video_width + int(140 * scale)) // 2 + 10
        widgets.append(GearIndicatorWidget(
            gx, top_y + 6, gw, gh, theme, font_path=font,
        ))

    if "turn" in enabled:
        tw = int(90 * scale)
        th = int(30 * scale)
        # Place turn signals to the right of gear
        turn_x = (video_width + int(140 * scale)) // 2 + 10
        turn_y = top_y + int(42 * scale)
        widgets.append(TurnSignalWidget(
            turn_x, turn_y, tw, th, theme,
        ))

    # === BOTTOM CENTER: Steering wheel with ACC/BRK gauges on either side ===
    steer_y = video_height - steer_size - my - int(20 * scale)
    steer_x = (video_width - steer_size) // 2

    if "steering" in enabled:
        widgets.append(SteeringWheelWidget(
            steer_x, steer_y, steer_size, steer_size, theme,
            font_path=font,
        ))

    # ACC gauge to the left of steering wheel
    if "accel" in enabled:
        ax = steer_x - gauge_w - 14
        ay = steer_y + (steer_size - gauge_h) // 2
        widgets.append(AccelGaugeWidget(
            ax, ay, gauge_w, gauge_h, theme, font_path=font,
        ))

    # BRK gauge to the right of steering wheel
    if "brake" in enabled:
        bx = steer_x + steer_size + 14
        by = steer_y + (steer_size - gauge_h) // 2
        widgets.append(BrakeIndicatorWidget(
            bx, by, gauge_w, gauge_h, theme, font_path=font,
        ))

    # === BOTTOM LEFT: Location/heading ===
    if "location" in enabled:
        lw = int(300 * scale)
        lh = int(44 * scale)
        lx = mx
        ly = video_height - lh - my
        widgets.append(LocationDisplayWidget(
            lx, ly, lw, lh, theme, font_path=font,
        ))

    return OverlayCanvas(video_width, video_height, widgets)


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
            # Use relative paths for portability
            rel = os.path.basename(png_path)
            f.write(f"file {rel}\n")
            f.write(f"duration {duration:.6f}\n")
        # Repeat last file (FFmpeg concat requires it for proper duration)
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
