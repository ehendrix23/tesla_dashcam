from __future__ import annotations

import sys

PLATFORM = sys.platform

DEFAULT_FONT_HALIGN = "CENTER"
DEFAULT_FONT_VALIGN = "BOTTOM"

DEFAULT_FONT = {
    "darwin": "/Library/Fonts/Arial Unicode.ttf",
    "win32": "/Windows/Fonts/arial.ttf",
    "cygwin": "/cygdrive/c/Windows/Fonts/arial.ttf",
    "linux": "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "freebsd11": "/usr/share/local/fonts/freefont-ttf/FreeSans.ttf",
}

HALIGN = {"LEFT": "10", "CENTER": "(w/2-text_w/2)", "RIGHT": "(w-text_w)"}

VALIGN = {"TOP": "10", "MIDDLE": "(h/2-(text_h/2))", "BOTTOM": "(h-(text_h)-10)"}

FFMPEG_LEFT_PERSPECTIVE = (
    ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000, "
    "perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:"
    "x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination"
)

FFMPEG_RIGHT_PERSPECTIVE = (
    ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000,"
    "perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:"
    "x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination"
)

__all__ = [
    "DEFAULT_FONT",
    "DEFAULT_FONT_HALIGN",
    "DEFAULT_FONT_VALIGN",
    "FFMPEG_LEFT_PERSPECTIVE",
    "FFMPEG_RIGHT_PERSPECTIVE",
    "HALIGN",
    "PLATFORM",
    "VALIGN",
]
