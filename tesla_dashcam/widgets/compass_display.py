"""Compass heading and GPS coordinate display widget."""

import math

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme

_COMPASS_DIRS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _heading_to_compass(heading_deg: float) -> str:
    idx = round(heading_deg / 22.5) % 16
    return _COMPASS_DIRS[idx]


class CompassDisplayWidget(Widget):
    """Renders heading (degrees + compass) and GPS coordinates on dark panel."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        return (
            "compass",
            round(frame.heading_deg),
            round(frame.latitude_deg, 4),
            round(frame.longitude_deg, 4),
        )

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=8,
            fill=(0, 0, 0, 160),
        )

        compass = _heading_to_compass(frame.heading_deg)

        # Fonts
        heading_font_size = max(12, self.height * 2 // 5)
        coord_font_size = max(9, self.height // 4)
        try:
            if self.font_path:
                heading_font = ImageFont.truetype(self.font_path, heading_font_size)
                coord_font = ImageFont.truetype(self.font_path, coord_font_size)
            else:
                heading_font = ImageFont.truetype("FreeSans.ttf", heading_font_size)
                coord_font = ImageFont.truetype("FreeSans.ttf", coord_font_size)
        except (OSError, IOError):
            heading_font = ImageFont.load_default()
            coord_font = heading_font

        # Draw small compass circle icon on the left
        icon_r = min(self.height // 3, 14)
        icon_cx = 8 + icon_r
        icon_cy = self.height // 3

        draw.ellipse(
            [icon_cx - icon_r, icon_cy - icon_r, icon_cx + icon_r, icon_cy + icon_r],
            outline=(160, 160, 160, 180),
            width=1,
        )

        # Heading arrow inside compass circle
        angle_rad = math.radians(frame.heading_deg - 90)
        arrow_len = icon_r - 3
        ax = icon_cx + int(arrow_len * math.cos(angle_rad))
        ay = icon_cy + int(arrow_len * math.sin(angle_rad))
        draw.line(
            [icon_cx, icon_cy, ax, ay],
            fill=(220, 60, 60, 230),
            width=2,
        )

        # Heading text: "81 E"
        text_x = icon_cx + icon_r + 8
        heading_text = f"{frame.heading_deg:.0f}\u00b0 {compass}"
        bbox = draw.textbbox((0, 0), heading_text, font=heading_font)
        th = bbox[3] - bbox[1]
        ty = 4 - bbox[1]
        draw.text((text_x, ty), heading_text, fill=(255, 255, 255, 240), font=heading_font)

        # GPS coordinates below
        coord_text = f"{frame.latitude_deg:.5f}, {frame.longitude_deg:.5f}"
        coord_y = ty + th + 4
        draw.text(
            (text_x, coord_y), coord_text,
            fill=(180, 180, 180, 200), font=coord_font,
        )

        return img
