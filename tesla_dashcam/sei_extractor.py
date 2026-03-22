"""
Tesla Dashcam SEI (Supplemental Enhancement Information) extractor.

Extracts telemetry data embedded in H.264 NAL units from Tesla dashcam MP4 files.
Based on Tesla's official implementation: https://github.com/teslamotors/dashcam

Requirements:
  - Tesla firmware 2025.44.25 or later
  - HW3 or above
  - Vehicle must be in motion (SEI data may not be present when parked)
"""

import logging
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Generator, List, Optional

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.internal.decoder import _DecodeVarint
from google.protobuf.internal.wire_format import WIRETYPE_VARINT, WIRETYPE_FIXED64, WIRETYPE_FIXED32

_LOGGER = logging.getLogger(__name__)


class GearState(IntEnum):
    """Vehicle gear state."""
    PARK = 0
    DRIVE = 1
    REVERSE = 2
    NEUTRAL = 3


class AutopilotState(IntEnum):
    """Autopilot engagement state."""
    NONE = 0
    SELF_DRIVING = 1
    AUTOSTEER = 2
    TACC = 3


@dataclass
class SeiFrame:
    """Telemetry data for a single video frame."""
    version: int = 0
    gear_state: GearState = GearState.PARK
    frame_seq_no: int = 0
    vehicle_speed_mps: float = 0.0
    accelerator_pedal_position: float = 0.0
    steering_wheel_angle: float = 0.0
    blinker_on_left: bool = False
    blinker_on_right: bool = False
    brake_applied: bool = False
    autopilot_state: AutopilotState = AutopilotState.NONE
    latitude_deg: float = 0.0
    longitude_deg: float = 0.0
    heading_deg: float = 0.0
    linear_acceleration_mps2_x: float = 0.0
    linear_acceleration_mps2_y: float = 0.0
    linear_acceleration_mps2_z: float = 0.0

    @property
    def speed_mph(self) -> float:
        """Vehicle speed in miles per hour."""
        return self.vehicle_speed_mps * 2.23694

    @property
    def speed_kmh(self) -> float:
        """Vehicle speed in kilometers per hour."""
        return self.vehicle_speed_mps * 3.6

    @property
    def gear_letter(self) -> str:
        """Single letter gear indicator (P/R/N/D)."""
        return {
            GearState.PARK: "P",
            GearState.DRIVE: "D",
            GearState.REVERSE: "R",
            GearState.NEUTRAL: "N",
        }.get(self.gear_state, "?")

    @property
    def autopilot_label(self) -> str:
        """Human-readable autopilot state."""
        return {
            AutopilotState.NONE: "",
            AutopilotState.SELF_DRIVING: "FSD",
            AutopilotState.AUTOSTEER: "AP",
            AutopilotState.TACC: "TACC",
        }.get(self.autopilot_state, "")

    @property
    def blinker_state(self) -> str:
        """Blinker state as string (left/right/hazard/off)."""
        if self.blinker_on_left and self.blinker_on_right:
            return "hazard"
        elif self.blinker_on_left:
            return "left"
        elif self.blinker_on_right:
            return "right"
        return ""


# Protobuf field definitions for SeiMetadata message
# Field number -> (name, wire_type, is_float, is_double, is_bool, enum_class)
_SEI_FIELDS = {
    1: ("version", WIRETYPE_VARINT, False, False, False, None),
    2: ("gear_state", WIRETYPE_VARINT, False, False, False, GearState),
    3: ("frame_seq_no", WIRETYPE_VARINT, False, False, False, None),
    4: ("vehicle_speed_mps", WIRETYPE_FIXED32, True, False, False, None),
    5: ("accelerator_pedal_position", WIRETYPE_FIXED32, True, False, False, None),
    6: ("steering_wheel_angle", WIRETYPE_FIXED32, True, False, False, None),
    7: ("blinker_on_left", WIRETYPE_VARINT, False, False, True, None),
    8: ("blinker_on_right", WIRETYPE_VARINT, False, False, True, None),
    9: ("brake_applied", WIRETYPE_VARINT, False, False, True, None),
    10: ("autopilot_state", WIRETYPE_VARINT, False, False, False, AutopilotState),
    11: ("latitude_deg", WIRETYPE_FIXED64, False, True, False, None),
    12: ("longitude_deg", WIRETYPE_FIXED64, False, True, False, None),
    13: ("heading_deg", WIRETYPE_FIXED64, False, True, False, None),
    14: ("linear_acceleration_mps2_x", WIRETYPE_FIXED64, False, True, False, None),
    15: ("linear_acceleration_mps2_y", WIRETYPE_FIXED64, False, True, False, None),
    16: ("linear_acceleration_mps2_z", WIRETYPE_FIXED64, False, True, False, None),
}


def _decode_protobuf(data: bytes) -> dict:
    """Decode protobuf binary data into a dictionary using SeiMetadata schema."""
    result = {}
    pos = 0
    length = len(data)

    while pos < length:
        try:
            # Decode field tag (field_number << 3 | wire_type)
            tag, new_pos = _DecodeVarint(data, pos)
            pos = new_pos
            field_number = tag >> 3
            wire_type = tag & 0x7

            if field_number not in _SEI_FIELDS:
                # Skip unknown field
                if wire_type == WIRETYPE_VARINT:
                    _, pos = _DecodeVarint(data, pos)
                elif wire_type == WIRETYPE_FIXED64:
                    pos += 8
                elif wire_type == WIRETYPE_FIXED32:
                    pos += 4
                else:
                    break
                continue

            field_name, expected_wire_type, is_float, is_double, is_bool, enum_class = _SEI_FIELDS[field_number]

            if wire_type == WIRETYPE_VARINT:
                value, pos = _DecodeVarint(data, pos)
                if is_bool:
                    value = bool(value)
                elif enum_class:
                    try:
                        value = enum_class(value)
                    except ValueError:
                        pass
            elif wire_type == WIRETYPE_FIXED32:
                value = struct.unpack("<f", data[pos:pos + 4])[0]
                pos += 4
            elif wire_type == WIRETYPE_FIXED64:
                if is_double:
                    value = struct.unpack("<d", data[pos:pos + 8])[0]
                else:
                    value = struct.unpack("<q", data[pos:pos + 8])[0]
                pos += 8
            else:
                break

            result[field_name] = value

        except (IndexError, struct.error):
            break

    return result


def _find_mdat(fp) -> tuple:
    """Find the mdat atom in an MP4 file.

    Returns:
        Tuple of (offset, size) for the mdat payload.
    """
    fp.seek(0)
    while True:
        header = fp.read(8)
        if len(header) < 8:
            raise RuntimeError("mdat atom not found")

        size32, atom_type = struct.unpack(">I4s", header)

        if size32 == 1:
            # Extended size
            large = fp.read(8)
            if len(large) != 8:
                raise RuntimeError("truncated extended atom size")
            atom_size = struct.unpack(">Q", large)[0]
            header_size = 16
        else:
            atom_size = size32 if size32 else 0
            header_size = 8

        if atom_type == b"mdat":
            payload_size = atom_size - header_size if atom_size else 0
            return fp.tell(), payload_size

        if atom_size < header_size:
            raise RuntimeError("invalid MP4 atom size")

        fp.seek(atom_size - header_size, 1)


def _strip_emulation_prevention_bytes(data: bytes) -> bytes:
    """Remove H.264 emulation prevention bytes (0x03 following 0x00 0x00)."""
    stripped = bytearray()
    zero_count = 0

    for byte in data:
        if zero_count >= 2 and byte == 0x03:
            zero_count = 0
            continue
        stripped.append(byte)
        zero_count = 0 if byte != 0 else zero_count + 1

    return bytes(stripped)


def _extract_proto_payload(nal: bytes) -> Optional[bytes]:
    """Extract protobuf payload from SEI NAL unit."""
    if not isinstance(nal, bytes) or len(nal) < 2:
        return None

    # Look for Tesla's SEI marker bytes (0x42 prefix, 0x69 start marker)
    for i in range(3, len(nal) - 1):
        byte = nal[i]
        if byte == 0x42:
            continue
        if byte == 0x69:
            if i > 2:
                return _strip_emulation_prevention_bytes(nal[i + 1:-1])
            break
        break

    return None


def _iter_nals(fp, offset: int, size: int) -> Generator[bytes, None, None]:
    """Yield SEI user NAL units from the MP4 mdat atom."""
    NAL_ID_SEI = 6
    NAL_SEI_ID_USER_DATA_UNREGISTERED = 5

    fp.seek(offset)
    consumed = 0

    while size == 0 or consumed < size:
        header = fp.read(4)
        if len(header) < 4:
            break

        nal_size = struct.unpack(">I", header)[0]
        if nal_size < 2:
            fp.seek(nal_size, 1)
            consumed += 4 + nal_size
            continue

        first_two = fp.read(2)
        if len(first_two) != 2:
            break

        # Check if this is an SEI NAL with user data
        if (first_two[0] & 0x1F) != NAL_ID_SEI or first_two[1] != NAL_SEI_ID_USER_DATA_UNREGISTERED:
            fp.seek(nal_size - 2, 1)
            consumed += 4 + nal_size
            continue

        rest = fp.read(nal_size - 2)
        if len(rest) != nal_size - 2:
            break

        payload = first_two + rest
        consumed += 4 + nal_size
        yield payload


def extract_sei_data(filepath: str) -> List[SeiFrame]:
    """Extract SEI telemetry data from a Tesla dashcam MP4 file.

    Args:
        filepath: Path to the MP4 video file.

    Returns:
        List of SeiFrame objects, one per frame with telemetry data.
        Returns empty list if no SEI data is found.
    """
    frames = []

    try:
        with open(filepath, "rb") as fp:
            try:
                offset, size = _find_mdat(fp)
            except RuntimeError as e:
                _LOGGER.debug("Could not find mdat atom in %s: %s", filepath, e)
                return frames

            for nal in _iter_nals(fp, offset, size):
                payload = _extract_proto_payload(nal)
                if not payload:
                    continue

                try:
                    data = _decode_protobuf(payload)
                    if data:
                        frame = SeiFrame(**data)
                        frames.append(frame)
                except Exception as e:
                    _LOGGER.debug("Failed to decode SEI frame: %s", e)
                    continue

    except FileNotFoundError:
        _LOGGER.warning("File not found: %s", filepath)
    except PermissionError:
        _LOGGER.warning("Permission denied: %s", filepath)
    except Exception as e:
        _LOGGER.debug("Error extracting SEI data from %s: %s", filepath, e)

    if frames:
        _LOGGER.info("Extracted %d SEI frames from %s", len(frames), filepath)
    else:
        _LOGGER.debug("No SEI data found in %s (requires firmware 2025.44.25+, HW3+)", filepath)

    return frames


def has_sei_data(filepath: str) -> bool:
    """Check if a video file contains SEI telemetry data.

    This is a quick check that stops after finding the first SEI frame.

    Args:
        filepath: Path to the MP4 video file.

    Returns:
        True if SEI data is present, False otherwise.
    """
    try:
        with open(filepath, "rb") as fp:
            try:
                offset, size = _find_mdat(fp)
            except RuntimeError:
                return False

            for nal in _iter_nals(fp, offset, size):
                payload = _extract_proto_payload(nal)
                if payload:
                    return True

    except Exception:
        pass

    return False


def export_sei_to_csv(frames: List[SeiFrame], output_path: str) -> None:
    """Export SEI data to a CSV file.

    Args:
        frames: List of SeiFrame objects.
        output_path: Path to write the CSV file.
    """
    if not frames:
        return

    import csv

    fieldnames = [
        "frame_seq_no", "vehicle_speed_mps", "speed_mph", "speed_kmh",
        "gear_state", "autopilot_state", "latitude_deg", "longitude_deg",
        "heading_deg", "steering_wheel_angle", "accelerator_pedal_position",
        "brake_applied", "blinker_on_left", "blinker_on_right",
        "linear_acceleration_mps2_x", "linear_acceleration_mps2_y",
        "linear_acceleration_mps2_z", "version"
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for frame in frames:
            row = {
                "frame_seq_no": frame.frame_seq_no,
                "vehicle_speed_mps": f"{frame.vehicle_speed_mps:.2f}",
                "speed_mph": f"{frame.speed_mph:.1f}",
                "speed_kmh": f"{frame.speed_kmh:.1f}",
                "gear_state": frame.gear_letter,
                "autopilot_state": frame.autopilot_label or "OFF",
                "latitude_deg": f"{frame.latitude_deg:.6f}",
                "longitude_deg": f"{frame.longitude_deg:.6f}",
                "heading_deg": f"{frame.heading_deg:.1f}",
                "steering_wheel_angle": f"{frame.steering_wheel_angle:.1f}",
                "accelerator_pedal_position": f"{frame.accelerator_pedal_position:.2f}",
                "brake_applied": "yes" if frame.brake_applied else "no",
                "blinker_on_left": "yes" if frame.blinker_on_left else "no",
                "blinker_on_right": "yes" if frame.blinker_on_right else "no",
                "linear_acceleration_mps2_x": f"{frame.linear_acceleration_mps2_x:.3f}",
                "linear_acceleration_mps2_y": f"{frame.linear_acceleration_mps2_y:.3f}",
                "linear_acceleration_mps2_z": f"{frame.linear_acceleration_mps2_z:.3f}",
                "version": frame.version,
            }
            writer.writerow(row)

    _LOGGER.info("Exported %d frames to %s", len(frames), output_path)
