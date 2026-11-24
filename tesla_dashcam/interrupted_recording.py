"""Tell an interrupted MP4 recording apart from an unreadable file.

When the car loses power or the USB drive is pulled while a clip is being written, the clip keeps its video data
but never gets its index (the moov box), so ffmpeg can't open it ("moov atom not found"). Only the first and last
4 MB of the file are read. Port of the top-level box check in https://crates.io/crates/vidfix-detect
"""

from __future__ import annotations

import os
import struct

WINDOW = 4 * 1024 * 1024


def _read_at(
    head: bytes, tail: bytes, file_len: int, offset: int, n: int
) -> bytes | None:
    if offset + n <= len(head):
        return head[offset : offset + n]
    tail_start = file_len - len(tail)
    if offset >= tail_start and offset + n <= file_len:
        return tail[offset - tail_start : offset - tail_start + n]
    return None


def _trailing_moov(tail: bytes, file_len: int, after: int) -> bool:
    tail_start = file_len - len(tail)
    i = tail.find(b"moov", 4)
    while i != -1:
        start = tail_start + i - 4
        if start >= after:
            (size,) = struct.unpack(">I", tail[i - 4 : i])
            if size >= 8 and start + size == file_len:
                return True
        i = tail.find(b"moov", i + 1)
    return False


def diagnose_bytes(head: bytes, tail: bytes, file_len: int) -> str | None:
    """A sentence describing the damage when this is an interrupted MP4/MOV, otherwise None."""
    offset = 0
    moov_complete = False
    mdat = None  # (payload_start, end, size_zeroed)
    while offset + 8 <= file_len:
        h = _read_at(head, tail, file_len, offset, 16) or _read_at(
            head, tail, file_len, offset, 8
        )
        if h is None:
            break
        box_type = h[4:8]
        if not all(32 <= c < 127 or c == 0xA9 for c in box_type):
            break
        (size,) = struct.unpack(">I", h[0:4])
        header = 8
        size_zeroed = size == 0
        if size == 1:
            if len(h) < 16:
                break
            (size,) = struct.unpack(">Q", h[8:16])
            header = 16
            size_zeroed = size == 0
        if size_zeroed:
            size = file_len - offset
        if size < header:
            break
        end = offset + size
        if box_type == b"moov" and end <= file_len:
            moov_complete = True
        if box_type == b"mdat":
            payload_end = min(end, file_len)
            if mdat is None or payload_end - offset > mdat[1] - mdat[0]:
                mdat = (offset + header, payload_end, size_zeroed)
            if size_zeroed:
                moov_complete = moov_complete or _trailing_moov(
                    tail, file_len, offset + header
                )
                break
        if end > file_len:
            break
        offset = end

    if mdat is None or mdat[1] <= mdat[0]:
        return None
    mb = round((mdat[1] - mdat[0]) / 1e6)
    if not moov_complete:
        return (
            f"the recording was interrupted before its index (moov) was written, for example because power was "
            f"lost or the drive was removed; {mb} MB of video data is still in the file and can usually be rebuilt"
        )
    if mdat[2]:
        return (
            f"the file's index is intact but the header in front of its video data is damaged; {mb} MB of video "
            f"data is still in the file and can usually be rebuilt"
        )
    return None


def diagnose_file(filename: str) -> str | None:
    """Like diagnose_bytes, for a file on disk. None when the file is fine, not an MP4, or can't be read."""
    try:
        file_len = os.path.getsize(filename)
        n = min(file_len, WINDOW)
        with open(filename, "rb") as f:
            head = f.read(n)
            f.seek(file_len - n)
            tail = f.read(n)
    except OSError:
        return None
    return diagnose_bytes(head, tail, file_len)
