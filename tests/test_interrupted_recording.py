import struct

from tesla_dashcam.interrupted_recording import diagnose_bytes, diagnose_file


def box(box_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload) + 8) + box_type + payload


FTYP = box(b"ftyp", b"isom\0\0\0\0")
MEDIA = b"\x07" * 5000
MOOV = box(b"moov", box(b"mvhd", b"\0" * 100))


def diagnose(data: bytes):
    return diagnose_bytes(data, data, len(data))


def test_healthy_clip():
    assert diagnose(FTYP + box(b"mdat", MEDIA) + MOOV) is None


def test_clip_cut_off_before_moov():
    msg = diagnose(FTYP + struct.pack(">I", 1_000_000) + b"mdat" + MEDIA)
    assert msg is not None and "interrupted" in msg


def test_mdat_size_zeroed_moov_at_end():
    msg = diagnose(FTYP + struct.pack(">I", 0) + b"mdat" + MEDIA + MOOV)
    assert msg is not None and "header" in msg


def test_moov_first_cut_short_still_plays():
    assert (
        diagnose(FTYP + MOOV + struct.pack(">I", 1_000_000) + b"mdat" + MEDIA) is None
    )


def test_not_mp4_and_missing_file(tmp_path):
    assert diagnose(b"hello, not a video") is None
    assert diagnose_file(str(tmp_path / "missing.mp4")) is None


def test_file_on_disk(tmp_path):
    clip = tmp_path / "2024-01-01_12-00-00-front.mp4"
    clip.write_bytes(FTYP + struct.pack(">I", 1_000_000) + b"mdat" + MEDIA)
    assert "interrupted" in diagnose_file(str(clip))
