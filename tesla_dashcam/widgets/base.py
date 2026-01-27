"""Base classes for graphical overlay widgets."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PIL import Image


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
