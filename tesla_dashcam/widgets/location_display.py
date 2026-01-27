"""Location and heading display widget."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme

_COMPASS_DIRS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _heading_to_compass(heading_deg: float) -> str:
    """Convert heading in degrees to compass direction."""
    idx = round(heading_deg / 22.5) % 16
    return _COMPASS_DIRS[idx]


class LocationDisplayWidget(Widget):
    """Renders GPS coordinates and compass heading on dark background."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        return (
            "loc",
            round(frame.latitude_deg, 4),
            round(frame.longitude_deg, 4),
            round(frame.heading_deg),
        )

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background panel
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=6,
            fill=(0, 0, 0, 140),
        )

        font_size = max(9, self.height // 2 - 4)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.truetype("FreeSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        compass = _heading_to_compass(frame.heading_deg)
        line1 = f"{frame.latitude_deg:.5f}, {frame.longitude_deg:.5f}"
        line2 = f"{frame.heading_deg:.0f}\u00b0 {compass}"

        draw.text((6, 2), line1, fill=(220, 220, 220, 240), font=font)
        draw.text((6, self.height // 2 + 1), line2, fill=(220, 220, 220, 240), font=font)

        return img
