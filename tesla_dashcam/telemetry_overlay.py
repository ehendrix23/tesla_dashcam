"""
Tesla Dashcam telemetry overlay generator.

Generates ASS (Advanced SubStation Alpha) subtitle files from SEI telemetry data
for frame-accurate overlay rendering with FFmpeg.
"""

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional

try:
    from .sei_extractor import SeiFrame
except ImportError:
    from sei_extractor import SeiFrame

_LOGGER = logging.getLogger(__name__)

# Tesla dashcam default frame rate
DEFAULT_FRAME_RATE = 36.0


@dataclass
class TelemetryOverlaySettings:
    """Configuration for telemetry overlay rendering."""
    format_string: str = "{speed} {gear} {autopilot}"
    position: str = "bottom-left"
    speed_unit: str = "mph"
    font_name: str = "Arial"
    font_size: int = 24
    font_color: str = "&H00FFFFFF"  # White in ASS BGR format
    outline_color: str = "&H00000000"  # Black outline
    outline_width: int = 2
    margin_x: int = 20
    margin_y: int = 20
    frame_rate: float = DEFAULT_FRAME_RATE


# ASS position alignment values
# 1=bottom-left, 2=bottom-center, 3=bottom-right
# 4=middle-left, 5=middle-center, 6=middle-right
# 7=top-left, 8=top-center, 9=top-right
_POSITION_TO_ALIGNMENT = {
    "bottom-left": 1,
    "bottom-center": 2,
    "bottom-right": 3,
    "middle-left": 4,
    "middle-center": 5,
    "center": 5,
    "middle-right": 6,
    "top-left": 7,
    "top-center": 8,
    "top-right": 9,
}


def _format_time(seconds: float) -> str:
    """Format seconds as ASS timestamp (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _format_frame(frame: SeiFrame, format_string: str, speed_unit: str) -> str:
    """Format a single frame's telemetry data according to the format string.

    Available format variables:
        {speed} - Speed with unit
        {speed_value} - Speed value only (no unit)
        {gear} - Gear letter (P/R/N/D)
        {autopilot} - Autopilot state (FSD/AP/TACC or empty)
        {brake} - "BRAKE" if applied, empty otherwise
        {blinker} - "< " for left, " >" for right, "<>" for hazard, empty otherwise
        {heading} - Compass heading in degrees
        {steering} - Steering wheel angle
        {accel} - Accelerator pedal position (0-100%)
        {lat} - Latitude
        {lon} - Longitude
        {gforce_x} - Lateral G-force
        {gforce_y} - Longitudinal G-force
    """
    # Calculate speed based on unit preference
    if speed_unit == "mph":
        speed_value = frame.speed_mph
        speed_formatted = f"{speed_value:.0f} mph"
    elif speed_unit == "kmh":
        speed_value = frame.speed_kmh
        speed_formatted = f"{speed_value:.0f} km/h"
    else:  # mps
        speed_value = frame.vehicle_speed_mps
        speed_formatted = f"{speed_value:.1f} m/s"

    # Format blinker indicator
    blinker = ""
    if frame.blinker_on_left and frame.blinker_on_right:
        blinker = "<>"
    elif frame.blinker_on_left:
        blinker = "< "
    elif frame.blinker_on_right:
        blinker = " >"

    # Build replacement dictionary
    replacements = {
        "speed": speed_formatted,
        "speed_value": f"{speed_value:.0f}",
        "gear": frame.gear_letter,
        "autopilot": frame.autopilot_label,
        "brake": "BRAKE" if frame.brake_applied else "",
        "blinker": blinker,
        "heading": f"{frame.heading_deg:.0f}",
        "steering": f"{frame.steering_wheel_angle:.0f}",
        "accel": f"{frame.accelerator_pedal_position:.0f}%",
        "lat": f"{frame.latitude_deg:.5f}",
        "lon": f"{frame.longitude_deg:.5f}",
        "gforce_x": f"{frame.linear_acceleration_mps2_x / 9.81:.2f}g",
        "gforce_y": f"{frame.linear_acceleration_mps2_y / 9.81:.2f}g",
    }

    # Perform replacements
    result = format_string
    for key, value in replacements.items():
        result = result.replace("{" + key + "}", str(value))

    # Clean up multiple spaces and trim
    while "  " in result:
        result = result.replace("  ", " ")

    return result.strip()


def _generate_ass_header(settings: TelemetryOverlaySettings) -> str:
    """Generate ASS file header with style definitions."""
    alignment = _POSITION_TO_ALIGNMENT.get(settings.position, 1)

    # Determine margins based on position
    margin_l = settings.margin_x if "left" in settings.position else 0
    margin_r = settings.margin_x if "right" in settings.position else 0
    margin_v = settings.margin_y

    return f"""[Script Info]
Title: Tesla Dashcam Telemetry
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Telemetry,{settings.font_name},{settings.font_size},{settings.font_color},&H000000FF,{settings.outline_color},&H80000000,1,0,0,0,100,100,0,0,1,{settings.outline_width},1,{alignment},{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def generate_telemetry_ass(
    frames: List[SeiFrame],
    settings: Optional[TelemetryOverlaySettings] = None,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """Generate an ASS subtitle file from SEI telemetry data.

    Args:
        frames: List of SeiFrame objects with telemetry data.
        settings: Overlay configuration settings. Uses defaults if None.
        output_path: Path to write the ASS file. Creates temp file if None.

    Returns:
        Path to the generated ASS file, or None if no frames provided.
    """
    if not frames:
        _LOGGER.debug("No frames provided for telemetry overlay")
        return None

    if settings is None:
        settings = TelemetryOverlaySettings()

    # Calculate frame duration
    frame_duration = 1.0 / settings.frame_rate

    # Generate ASS content
    content = _generate_ass_header(settings)

    # Track last formatted text to avoid duplicate entries
    last_text = None
    last_start_time = 0.0

    for i, frame in enumerate(frames):
        current_time = i * frame_duration
        text = _format_frame(frame, settings.format_string, settings.speed_unit)

        # Escape ASS special characters
        text = text.replace("\\", "\\\\")
        text = text.replace("{", "\\{")
        text = text.replace("}", "\\}")

        # Only create new dialogue when text changes (reduces file size)
        if text != last_text:
            if last_text is not None:
                # Close previous dialogue
                start_ts = _format_time(last_start_time)
                end_ts = _format_time(current_time)
                content += f"Dialogue: 0,{start_ts},{end_ts},Telemetry,,0,0,0,,{last_text}\n"

            last_text = text
            last_start_time = current_time

    # Close final dialogue
    if last_text is not None:
        final_time = len(frames) * frame_duration
        start_ts = _format_time(last_start_time)
        end_ts = _format_time(final_time)
        content += f"Dialogue: 0,{start_ts},{end_ts},Telemetry,,0,0,0,,{last_text}\n"

    # Write to file
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".ass", prefix="tesla_telemetry_")
        os.close(fd)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    _LOGGER.info("Generated telemetry overlay: %s (%d frames)", output_path, len(frames))
    return output_path


def get_sei_overlay_stats(frames: List[SeiFrame], speed_unit: str = "mph") -> dict:
    """Calculate summary statistics from SEI data for static overlay variables.

    Args:
        frames: List of SeiFrame objects.
        speed_unit: Speed unit for calculations (mph, kmh, mps).

    Returns:
        Dictionary with summary statistics.
    """
    if not frames:
        return {
            "sei_available": "no",
            "sei_frame_count": 0,
            "sei_avg_speed": "n/a",
            "sei_max_speed": "n/a",
            "sei_start_lat": "n/a",
            "sei_start_lon": "n/a",
            "sei_end_lat": "n/a",
            "sei_end_lon": "n/a",
        }

    # Calculate speeds based on unit
    if speed_unit == "mph":
        speeds = [f.speed_mph for f in frames]
        unit_suffix = " mph"
    elif speed_unit == "kmh":
        speeds = [f.speed_kmh for f in frames]
        unit_suffix = " km/h"
    else:
        speeds = [f.vehicle_speed_mps for f in frames]
        unit_suffix = " m/s"

    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    max_speed = max(speeds) if speeds else 0

    return {
        "sei_available": "yes",
        "sei_frame_count": len(frames),
        "sei_avg_speed": f"{avg_speed:.1f}{unit_suffix}",
        "sei_max_speed": f"{max_speed:.1f}{unit_suffix}",
        "sei_start_lat": f"{frames[0].latitude_deg:.5f}" if frames else "n/a",
        "sei_start_lon": f"{frames[0].longitude_deg:.5f}" if frames else "n/a",
        "sei_end_lat": f"{frames[-1].latitude_deg:.5f}" if frames else "n/a",
        "sei_end_lon": f"{frames[-1].longitude_deg:.5f}" if frames else "n/a",
    }
