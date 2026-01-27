"""Compass heading and GPS coordinate display widget."""

import math

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme, get_font

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
        heading_font_size = max(12, self.height // 3)
        coord_font_size = max(9, self.height // 5)
        heading_font = get_font(heading_font_size, self.font_path)
        coord_font = get_font(coord_font_size, self.font_path)

        # Draw compass circle icon on the left (capped to avoid eating text space)
        icon_r = min(max(8, self.height // 4), 22)
        icon_cx = 6 + icon_r
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
        avail_heading_w = self.width - text_x - 6
        heading_text = f"{frame.heading_deg:.0f}\u00b0 {compass}"
        bbox = draw.textbbox((0, 0), heading_text, font=heading_font)
        # If heading text overflows, try smaller font
        if (bbox[2] - bbox[0]) > avail_heading_w and heading_font_size > 14:
            heading_font = get_font(heading_font_size - 4, self.font_path)
            bbox = draw.textbbox((0, 0), heading_text, font=heading_font)
        th = bbox[3] - bbox[1]
        ty = 4 - bbox[1]
        draw.text((text_x, ty), heading_text, fill=(255, 255, 255, 240), font=heading_font)

        # GPS coordinates below - use precision that fits available width
        avail_text_w = self.width - text_x - 6
        coord_text = f"{frame.latitude_deg:.4f}, {frame.longitude_deg:.4f}"
        # Check if it fits, reduce precision if not
        cbbox = draw.textbbox((0, 0), coord_text, font=coord_font)
        if (cbbox[2] - cbbox[0]) > avail_text_w:
            coord_text = f"{frame.latitude_deg:.3f}, {frame.longitude_deg:.3f}"
        coord_y = ty + th + 4
        draw.text(
            (text_x, coord_y), coord_text,
            fill=(180, 180, 180, 200), font=coord_font,
        )

        return img
