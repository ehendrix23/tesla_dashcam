"""Base classes for graphical overlay widgets."""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PIL import Image, ImageFont

# System font search paths (platform-dependent)
_FONT_CANDIDATES = [
    "FreeSans.ttf",  # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux alt
]
if sys.platform == "darwin":
    _FONT_CANDIDATES = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ] + _FONT_CANDIDATES
elif sys.platform == "win32":
    _FONT_CANDIDATES = [
        "C:/Windows/Fonts/arial.ttf",
    ] + _FONT_CANDIDATES

_RESOLVED_FONT: Optional[str] = None


def get_font(size: int, font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    """Load a TrueType font at the given size.

    Tries user-specified path, then system fonts, then Pillow's built-in default.
    """
    global _RESOLVED_FONT

    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            pass

    # Use cached system font if already resolved
    if _RESOLVED_FONT is not None:
        try:
            return ImageFont.truetype(_RESOLVED_FONT, size)
        except (OSError, IOError):
            _RESOLVED_FONT = None

    # Search for a system font
    for candidate in _FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(candidate, size)
            _RESOLVED_FONT = candidate
            return f
        except (OSError, IOError):
            continue

    # Last resort: Pillow built-in (supports size in Pillow >= 10.1)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


@dataclass
class WidgetTheme:
    """Color theme for widgets (RGBA tuples)."""

    primary: Tuple[int, int, int, int] = (255, 255, 255, 230)
    active: Tuple[int, int, int, int] = (0, 200, 0, 255)
    inactive: Tuple[int, int, int, int] = (80, 80, 80, 120)
    warning: Tuple[int, int, int, int] = (220, 40, 40, 255)
    text: Tuple[int, int, int, int] = (255, 255, 255, 240)
    background: Tuple[int, int, int, int] = (0, 0, 0, 140)
    accent: Tuple[int, int, int, int] = (255, 180, 0, 255)


THEME_PRESETS = {
    "default": WidgetTheme(),
    "hud": WidgetTheme(
        primary=(0, 255, 100, 230),
        active=(0, 255, 100, 255),
        inactive=(0, 80, 30, 120),
        warning=(255, 60, 60, 255),
        text=(0, 255, 100, 240),
        background=(0, 0, 0, 100),
        accent=(0, 200, 80, 255),
    ),
    "minimal": WidgetTheme(
        primary=(200, 200, 200, 180),
        active=(180, 220, 180, 220),
        inactive=(60, 60, 60, 80),
        warning=(200, 60, 60, 200),
        text=(200, 200, 200, 200),
        background=(0, 0, 0, 80),
        accent=(200, 160, 0, 200),
    ),
    "performance": WidgetTheme(
        primary=(255, 60, 60, 230),
        active=(255, 100, 0, 255),
        inactive=(60, 60, 60, 120),
        warning=(255, 0, 0, 255),
        text=(255, 255, 255, 240),
        background=(20, 20, 20, 180),
        accent=(255, 200, 0, 255),
    ),
}


class Widget:
    """Base class for overlay widgets."""

    def __init__(self, x: int, y: int, width: int, height: int, theme: WidgetTheme):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.theme = theme

    def state_key(self, frame) -> tuple:
        """Return hashable key for deduplication. Override in subclasses."""
        raise NotImplementedError

    def render(self, frame) -> Image.Image:
        """Render widget for frame. Returns RGBA Image. Override in subclasses."""
        raise NotImplementedError


class OverlayCanvas:
    """Full overlay canvas that composites all widgets."""

    def __init__(self, width: int, height: int, widgets: List[Widget]):
        self.width = width
        self.height = height
        self.widgets = widgets

    def composite_state_key(self, frame) -> tuple:
        """Combined state key across all widgets."""
        return tuple(w.state_key(frame) for w in self.widgets)

    def render(self, frame) -> Image.Image:
        """Render all widgets onto a transparent canvas."""
        canvas = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        for widget in self.widgets:
            widget_img = widget.render(frame)
            canvas.paste(widget_img, (widget.x, widget.y), widget_img)
        return canvas
