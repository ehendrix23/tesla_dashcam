"""Telemetry panel renderer.

Generates camera-sized panels for compositing into the multi-camera video
layout. Two panels are supported:

- **Instruments panel**: steering wheel, speed, gauges, gear, turn signals,
  compass, G-force, and acceleration indicators on a dark background.
- **Map panel**: route map with a moving position dot that zooms in/out
  based on vehicle speed.

Each panel is rendered as PNG frames with an FFmpeg concat demuxer file.
"""

import logging
import math
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

try:
    from .sei_extractor import SeiFrame
except ImportError:
    from sei_extractor import SeiFrame

from .graphical_overlay import (
    GraphicalOverlaySettings,
    _resolve_widgets,
    DEFAULT_FRAME_RATE,
)
from .widgets.base import (
    OverlayCanvas,
    WidgetTheme,
    THEME_PRESETS,
    get_font,
)
from .widgets.steering_wheel import SteeringWheelWidget
from .widgets.turn_signals import TurnSignalWidget
from .widgets.brake_indicator import BrakeIndicatorWidget
from .widgets.accel_gauge import AccelGaugeWidget
from .widgets.speed_display import SpeedDisplayWidget
from .widgets.gear_indicator import GearIndicatorWidget
from .widgets.datetime_display import DateTimeDisplayWidget
from .widgets.autopilot_indicator import AutopilotIndicatorWidget
from .widgets.gforce_display import GForceDisplayWidget
from .widgets.compass_display import CompassDisplayWidget
from .widgets.center_cluster import CenterClusterWidget
from .widgets.elevation_display import ElevationDisplayWidget

_LOGGER = logging.getLogger(__name__)

try:
    import staticmap
    _HAS_STATICMAP = True
except ImportError:
    _HAS_STATICMAP = False


# ---------------------------------------------------------------------------
# Instruments panel layout
# ---------------------------------------------------------------------------

def _build_instruments_canvas(
    width: int,
    height: int,
    settings: GraphicalOverlaySettings,
) -> OverlayCanvas:
    """Build a full-panel instruments layout.

    The full panel height is used for widgets -- no map section.
    Layout:
        Row 1 (top):   [DateTime] [Speed+AP] [Gear] [Compass]
        Row 2 (center): Full-width cluster (steering + gauges)
        Row 3 (narrow): Turn signals strip
        Row 4 (bottom): [G-force] [Elevation/Accel]
    """
    theme = THEME_PRESETS.get(settings.theme_name, THEME_PRESETS["default"])
    enabled = _resolve_widgets(settings.widgets)
    font = settings.font_path

    pad = max(4, width // 60)
    gap = max(3, pad // 2)
    usable_w = width - 2 * pad
    usable_h = height - 2 * pad

    widgets = []

    # --- Row 1 (top ~20%): DateTime | Speed+AP | Gear | Compass ---
    row1_h = int(usable_h * 0.20)
    row1_y = pad

    dt_w = int(usable_w * 0.30)
    if "datetime" in enabled:
        widgets.append(DateTimeDisplayWidget(
            pad, row1_y, dt_w, row1_h, theme,
            start_time=settings.start_time,
            frame_rate=settings.frame_rate,
            font_path=font,
        ))

    speed_w = int(usable_w * 0.24)
    speed_x = pad + dt_w + gap
    if "speed" in enabled:
        show_ap = "autopilot" in enabled
        widgets.append(SpeedDisplayWidget(
            speed_x, row1_y, speed_w, row1_h, theme,
            speed_unit=settings.speed_unit,
            show_autopilot=show_ap,
            font_path=font,
        ))

    gear_w = int(usable_w * 0.16)
    gear_x = speed_x + speed_w + gap
    if "gear" in enabled:
        widgets.append(GearIndicatorWidget(
            gear_x, row1_y, gear_w, row1_h, theme,
            font_path=font,
        ))

    compass_x = gear_x + gear_w + gap
    compass_w = usable_w - (compass_x - pad)
    if "compass" in enabled:
        widgets.append(CompassDisplayWidget(
            compass_x, row1_y, compass_w, row1_h, theme,
            font_path=font,
        ))

    # --- Row 2 (~52%): Full-width cluster (steering + acc/brk gauges) ---
    row2_y = row1_y + row1_h + gap
    row2_h = int(usable_h * 0.52)

    steer_sz = int(row2_h * 0.70)
    gw = max(20, int(usable_w * 0.08))
    gh = int(row2_h * 0.40)

    if "cluster" in enabled:
        widgets.append(CenterClusterWidget(
            pad, row2_y, usable_w, row2_h, theme,
            steering_size=steer_sz, gauge_w=gw, gauge_h=gh,
            font_path=font,
            show_gforce=False,
        ))

    # --- Row 3 (~8%): Turn signals strip ---
    row3_y = row2_y + row2_h + gap
    turn_h = int(usable_h * 0.08)
    if "turn" in enabled:
        max_turn_w = min(usable_w, int(turn_h * 6))
        turn_x = pad + (usable_w - max_turn_w) // 2
        widgets.append(TurnSignalWidget(
            turn_x, row3_y, max_turn_w, turn_h, theme,
        ))

    # --- Row 4 (~18%): G-force (left) | Elevation/Accel (right) side by side ---
    row4_y = row3_y + turn_h + gap
    row4_h = height - row4_y - pad
    half_w = (usable_w - gap) // 2

    if "gforce" in enabled:
        widgets.append(GForceDisplayWidget(
            pad, row4_y, half_w, row4_h, theme,
            font_path=font,
        ))

    if "elevation" in enabled:
        widgets.append(ElevationDisplayWidget(
            pad + half_w + gap, row4_y, half_w, row4_h, theme,
            font_path=font,
        ))

    return OverlayCanvas(width, height, widgets)


# ---------------------------------------------------------------------------
# Route map
# ---------------------------------------------------------------------------

class _RouteMap:
    """Route map with speed-adaptive zoom and accurate position tracking.

    Renders the full route at a large internal resolution, then for each
    frame crops a window centered on the current position. The crop size
    varies with speed: zoomed in when slow, zoomed out when fast.
    """

    _ZOOM_TABLE = [
        (2.0, 0.30),    # < ~5 mph: tight crop
        (10.0, 0.50),   # < ~22 mph: neighborhood
        (25.0, 0.75),   # < ~56 mph: wider area
        (999.0, 1.0),   # highway: full route
    ]

    def __init__(
        self,
        coords: List[Tuple[float, float]],
        display_width: int,
        display_height: int,
    ):
        self.display_width = display_width
        self.display_height = display_height
        self.coords = coords

        self._base_w = display_width * 2
        self._base_h = display_height * 2

        self.lons = [c[0] for c in coords]
        self.lats = [c[1] for c in coords]
        self.min_lon = min(self.lons)
        self.max_lon = max(self.lons)
        self.min_lat = min(self.lats)
        self.max_lat = max(self.lats)

        self.base_img = self._try_staticmap()
        self._is_staticmap = self.base_img is not None
        if self.base_img is None:
            self.base_img = self._draw_path_only()

    def _try_staticmap(self) -> Optional[Image.Image]:
        if not _HAS_STATICMAP:
            return None
        try:
            m = staticmap.StaticMap(self._base_w, self._base_h)
            m.add_line(staticmap.Line(self.coords, "white", 6))
            m.add_line(staticmap.Line(self.coords, "#1E90FF", 4))
            m.add_marker(staticmap.CircleMarker(self.coords[0], "#00CC00", 10))
            m.add_marker(staticmap.CircleMarker(self.coords[-1], "#FF4444", 10))
            img = m.render()
            if hasattr(m, 'x_center') and hasattr(m, 'y_center') and hasattr(m, 'zoom'):
                self._sm_x_center = m.x_center
                self._sm_y_center = m.y_center
                self._sm_zoom = m.zoom
            return img.convert("RGBA")
        except Exception as exc:
            _LOGGER.debug("staticmap render failed: %s", exc)
            return None

    def _draw_path_only(self) -> Image.Image:
        img = Image.new("RGBA", (self._base_w, self._base_h), (30, 30, 35, 255))
        draw = ImageDraw.Draw(img)
        for i in range(1, 4):
            y = int(self._base_h * i / 4)
            draw.line([(0, y), (self._base_w, y)], fill=(50, 50, 55, 120), width=1)
            x = int(self._base_w * i / 4)
            draw.line([(x, 0), (x, self._base_h)], fill=(50, 50, 55, 120), width=1)

        pixels = [self._gps_to_base_pixel(lon, lat) for lon, lat in self.coords]
        if len(pixels) >= 2:
            draw.line(pixels, fill=(255, 255, 255, 100), width=8, joint="curve")
            draw.line(pixels, fill=(30, 144, 255, 220), width=5, joint="curve")
        if pixels:
            sx, sy = pixels[0]
            draw.ellipse([sx - 7, sy - 7, sx + 7, sy + 7], fill=(0, 200, 0, 220))
            ex, ey = pixels[-1]
            draw.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], fill=(255, 60, 60, 220))
        return img

    def _gps_to_base_pixel(self, lon: float, lat: float) -> Tuple[int, int]:
        if self._is_staticmap:
            return self._gps_to_pixel_mercator(lon, lat)
        return self._gps_to_pixel_linear(lon, lat)

    def _gps_to_pixel_linear(self, lon: float, lat: float) -> Tuple[int, int]:
        lon_range = max(self.max_lon - self.min_lon, 0.001)
        lat_range = max(self.max_lat - self.min_lat, 0.001)
        pad = 0.20
        min_lon = self.min_lon - lon_range * pad
        max_lon = self.max_lon + lon_range * pad
        min_lat = self.min_lat - lat_range * pad
        max_lat = self.max_lat + lat_range * pad

        if max_lon - min_lon > 1e-7:
            px = int((lon - min_lon) / (max_lon - min_lon) * self._base_w)
        else:
            px = self._base_w // 2
        if max_lat - min_lat > 1e-7:
            py = int((max_lat - lat) / (max_lat - min_lat) * self._base_h)
        else:
            py = self._base_h // 2
        return (max(0, min(self._base_w - 1, px)),
                max(0, min(self._base_h - 1, py)))

    def _gps_to_pixel_mercator(self, lon: float, lat: float) -> Tuple[int, int]:
        zoom = self._sm_zoom
        n = 2.0 ** zoom
        tile_sz = 256
        x_tile = (lon + 180.0) / 360.0 * n
        lat_rad = math.radians(lat)
        y_tile = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
        px = int((x_tile - self._sm_x_center) * tile_sz + self._base_w / 2)
        py = int((y_tile - self._sm_y_center) * tile_sz + self._base_h / 2)
        return (max(0, min(self._base_w - 1, px)),
                max(0, min(self._base_h - 1, py)))

    def _crop_fraction(self, speed_mps: float) -> float:
        for threshold, fraction in self._ZOOM_TABLE:
            if speed_mps < threshold:
                return fraction
        return 1.0

    def render_frame(
        self, lat: float, lon: float, speed_mps: float = 0.0,
    ) -> Image.Image:
        """Return a cropped map view centered on current position with dot."""
        cx, cy = self._gps_to_base_pixel(lon, lat)

        frac = self._crop_fraction(abs(speed_mps))
        crop_w = max(self.display_width, int(self._base_w * frac))
        crop_h = max(self.display_height, int(self._base_h * frac))

        x1 = max(0, min(self._base_w - crop_w, cx - crop_w // 2))
        y1 = max(0, min(self._base_h - crop_h, cy - crop_h // 2))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        cropped = self.base_img.crop((x1, y1, x2, y2))
        if cropped.size != (self.display_width, self.display_height):
            cropped = cropped.resize(
                (self.display_width, self.display_height), Image.LANCZOS,
            )

        dot_x = int((cx - x1) / crop_w * self.display_width)
        dot_y = int((cy - y1) / crop_h * self.display_height)
        dot_x = max(0, min(self.display_width - 1, dot_x))
        dot_y = max(0, min(self.display_height - 1, dot_y))

        draw = ImageDraw.Draw(cropped)
        r_outer = 10
        draw.ellipse(
            [dot_x - r_outer, dot_y - r_outer,
             dot_x + r_outer, dot_y + r_outer],
            fill=(0, 80, 200, 100),
        )
        r = 7
        draw.ellipse(
            [dot_x - r, dot_y - r, dot_x + r, dot_y + r],
            fill=(255, 255, 255, 250),
        )
        draw.ellipse(
            [dot_x - r + 2, dot_y - r + 2,
             dot_x + r - 2, dot_y + r - 2],
            fill=(30, 120, 255, 255),
        )
        return cropped


# ---------------------------------------------------------------------------
# Shared rendering logic
# ---------------------------------------------------------------------------

def _render_concat(
    frames: List[SeiFrame],
    frame_rate: float,
    output_dir: str,
    prefix: str,
    render_fn,
) -> Optional[str]:
    """Render unique states to PNGs and write an FFmpeg concat demuxer file.

    Args:
        frames: SEI frames to iterate.
        frame_rate: Frames per second.
        output_dir: Directory for PNG output.
        prefix: Filename prefix for PNGs and concat file.
        render_fn: Callable(frame) -> (Image, state_key_tuple).

    Returns:
        Path to the concat file, or None if empty.
    """
    frame_duration = 1.0 / frame_rate
    state_cache: Dict[tuple, str] = {}
    concat_entries = []
    state_counter = 0
    last_key = None
    last_count = 0

    for frame in frames:
        img, key = render_fn(frame)

        if key == last_key:
            last_count += 1
            continue

        if last_key is not None:
            concat_entries.append((state_cache[last_key], last_count * frame_duration))

        if key not in state_cache:
            png_name = f"{prefix}_{state_counter:06d}.png"
            png_path = os.path.join(output_dir, png_name)
            img.save(png_path, "PNG")
            state_cache[key] = png_path
            state_counter += 1

        last_key = key
        last_count = 1

    if last_key is not None:
        concat_entries.append((state_cache[last_key], last_count * frame_duration))

    if not concat_entries:
        return None

    concat_path = os.path.join(output_dir, f"{prefix}_concat.txt")
    with open(concat_path, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for png_path, duration in concat_entries:
            # Use full path with forward slashes for Windows compatibility
            safe_path = png_path.replace(os.sep, "/")
            f.write(f"file {safe_path}\n")
            f.write(f"duration {duration:.6f}\n")
        if concat_entries:
            safe_path = concat_entries[-1][0].replace(os.sep, "/")
            f.write(f"file {safe_path}\n")

    _LOGGER.info(
        "Generated %s panel: %d unique states, %d frames, dir=%s",
        prefix, state_counter, len(frames), output_dir,
    )
    return concat_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_instruments_panel(
    frames: List[SeiFrame],
    panel_width: int,
    panel_height: int,
    settings: Optional[GraphicalOverlaySettings] = None,
    output_dir: Optional[str] = None,
) -> Optional[str]:
    """Generate the instruments panel as PNG frames with concat file.

    Returns:
        Path to the FFmpeg concat demuxer file, or None.
    """
    if not frames:
        return None
    if settings is None:
        settings = GraphicalOverlaySettings()

    canvas = _build_instruments_canvas(panel_width, panel_height, settings)

    created_dir = False
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tesla_instr_")
        created_dir = True
    elif not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        created_dir = True

    def render_fn(frame):
        bg = Image.new("RGBA", (panel_width, panel_height), (20, 20, 25, 255))
        widget_img = canvas.render(frame)
        bg = Image.alpha_composite(bg, widget_img)
        key = canvas.composite_state_key(frame)
        return bg, key

    result = _render_concat(
        frames, settings.frame_rate, output_dir, "instr", render_fn,
    )
    if result is None and created_dir:
        shutil.rmtree(output_dir, ignore_errors=True)
    return result


def generate_map_panel(
    frames: List[SeiFrame],
    panel_width: int,
    panel_height: int,
    settings: Optional[GraphicalOverlaySettings] = None,
    output_dir: Optional[str] = None,
) -> Optional[str]:
    """Generate the map panel as PNG frames with concat file.

    Returns:
        Path to the FFmpeg concat demuxer file, or None.
    """
    if not frames:
        return None
    if settings is None:
        settings = GraphicalOverlaySettings()

    # Collect GPS coordinates
    coords: List[Tuple[float, float]] = []
    seen = set()
    for frame in frames:
        if abs(frame.latitude_deg) > 0.001 or abs(frame.longitude_deg) > 0.001:
            key = (round(frame.longitude_deg, 5), round(frame.latitude_deg, 5))
            if key not in seen:
                seen.add(key)
                coords.append((frame.longitude_deg, frame.latitude_deg))

    if len(coords) < 2:
        _LOGGER.debug("Not enough GPS coordinates for map panel")
        return None

    route_map = _RouteMap(coords, panel_width, panel_height)

    created_dir = False
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tesla_map_")
        created_dir = True
    elif not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        created_dir = True

    def render_fn(frame):
        img = route_map.render_frame(
            frame.latitude_deg, frame.longitude_deg,
            speed_mps=frame.vehicle_speed_mps,
        )
        speed_q = round(frame.vehicle_speed_mps / 2.0) * 2.0
        key = (round(frame.latitude_deg, 4),
               round(frame.longitude_deg, 4),
               speed_q)
        return img, key

    result = _render_concat(
        frames, settings.frame_rate, output_dir, "map", render_fn,
    )
    if result is None and created_dir:
        shutil.rmtree(output_dir, ignore_errors=True)
    return result


# Keep backward compat -- single combined panel
def generate_telemetry_panel(
    frames: List[SeiFrame],
    panel_width: int,
    panel_height: int,
    settings: Optional[GraphicalOverlaySettings] = None,
    output_dir: Optional[str] = None,
    include_map: bool = True,
) -> Optional[str]:
    """Generate a combined instruments+map panel (legacy single-panel mode)."""
    return generate_instruments_panel(
        frames, panel_width, panel_height, settings, output_dir,
    )


def cleanup_panel_dir(concat_path: str) -> None:
    """Remove the temporary panel directory."""
    if concat_path:
        panel_dir = os.path.dirname(concat_path)
        if panel_dir and os.path.isdir(panel_dir):
            # Retry cleanup for Windows where files may still be locked by FFmpeg
            for attempt in range(3):
                try:
                    shutil.rmtree(panel_dir)
                    _LOGGER.debug("Cleaned up panel dir: %s", panel_dir)
                    return
                except OSError:
                    if attempt < 2:
                        import time
                        time.sleep(0.5)
            # Final attempt with ignore_errors
            shutil.rmtree(panel_dir, ignore_errors=True)
            _LOGGER.debug("Cleaned up panel dir (with errors ignored): %s", panel_dir)
