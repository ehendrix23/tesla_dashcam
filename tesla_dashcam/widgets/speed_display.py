"""Speed display widget."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class SpeedDisplayWidget(Widget):
    """Renders a large speed number with unit."""

    def __init__(self, x, y, width, height, theme, speed_unit="mph", font_path=None):
        super().__init__(x, y, width, height, theme)
        self.speed_unit = speed_unit
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        if self.speed_unit == "mph":
            return ("speed", round(frame.speed_mph))
        elif self.speed_unit == "kmh":
            return ("speed", round(frame.speed_kmh))
        return ("speed", round(frame.vehicle_speed_mps, 1))

    def _get_speed(self, frame):
        if self.speed_unit == "mph":
            return frame.speed_mph, "mph"
        elif self.speed_unit == "kmh":
            return frame.speed_kmh, "km/h"
        return frame.vehicle_speed_mps, "m/s"

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        speed_val, unit_str = self._get_speed(frame)
        speed_text = f"{speed_val:.0f}"

        # Load fonts
        big_size = self.height * 2 // 3
        small_size = self.height // 4
        try:
            if self.font_path:
                big_font = ImageFont.truetype(self.font_path, big_size)
                small_font = ImageFont.truetype(self.font_path, small_size)
            else:
                big_font = ImageFont.truetype("FreeSans.ttf", big_size)
                small_font = ImageFont.truetype("FreeSans.ttf", small_size)
        except (OSError, IOError):
            big_font = ImageFont.load_default()
            small_font = big_font

        # Draw speed number
        bbox = draw.textbbox((0, 0), speed_text, font=big_font)
        tw = bbox[2] - bbox[0]
        tx = (self.width - tw) // 2
        draw.text(
            (tx, 0),
            speed_text,
            fill=self.theme.text,
            font=big_font,
        )

        # Draw unit below
        bbox_u = draw.textbbox((0, 0), unit_str, font=small_font)
        uw = bbox_u[2] - bbox_u[0]
        ux = (self.width - uw) // 2
        draw.text(
            (ux, big_size + 2),
            unit_str,
            fill=(*self.theme.text[:3], self.theme.text[3] * 3 // 4),
            font=small_font,
        )

        return img
