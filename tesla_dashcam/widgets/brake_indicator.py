"""Brake indicator widget."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class BrakeIndicatorWidget(Widget):
    """Renders a brake indicator that lights up red when applied."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        return ("brake", frame.brake_applied)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        color = self.theme.warning if frame.brake_applied else self.theme.inactive
        radius = min(self.width, self.height) // 2 - 2
        cx = self.width // 2
        cy = self.height // 2

        # Filled circle
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=color,
        )

        # "B" label
        font_size = max(10, radius)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.truetype("FreeSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        text_color = (255, 255, 255, 255) if frame.brake_applied else (120, 120, 120, 180)
        bbox = draw.textbbox((0, 0), "B", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (cx - tw // 2, cy - th // 2 - bbox[1]),
            "B",
            fill=text_color,
            font=font,
        )

        return img
