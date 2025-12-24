from __future__ import annotations

from datetime import datetime

DISPLAY_TS = False


def get_current_timestamp() -> str:
    """Returns the current timestamp prefix when enabled."""
    if DISPLAY_TS:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S - ")
    return ""


__all__ = ["DISPLAY_TS", "get_current_timestamp"]
