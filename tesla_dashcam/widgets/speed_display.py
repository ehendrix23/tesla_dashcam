"""Speed display widget - large readable speed with unit."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class SpeedDisplayWidget(Widget):
    """Renders a large speed number with unit on a dark background panel."""

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
            return frame.speed_mph, "MPH"
        elif self.speed_unit == "kmh":
            return frame.speed_kmh, "KM/H"
        return frame.vehicle_speed_mps, "M/S"

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background panel
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=8,
            fill=(0, 0, 0, 140),
        )

        speed_val, unit_str = self._get_speed(frame)
        speed_text = f"{speed_val:.0f}"

        # Load fonts
        big_size = self.height * 3 // 5
        small_size = max(10, self.height // 5)
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

        # Draw speed number (white, bold)
        bbox = draw.textbbox((0, 0), speed_text, font=big_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (self.width - tw) // 2
        ty = (self.height - th) // 2 - bbox[1] - small_size // 2
        draw.text(
            (tx, ty),
            speed_text,
            fill=(255, 255, 255, 255),
            font=big_font,
        )

        # Draw unit below speed
        bbox_u = draw.textbbox((0, 0), unit_str, font=small_font)
        uw = bbox_u[2] - bbox_u[0]
        ux = (self.width - uw) // 2
        uy = ty + th + 2
        draw.text(
            (ux, uy),
            unit_str,
            fill=(200, 200, 200, 220),
            font=small_font,
        )

        return img
