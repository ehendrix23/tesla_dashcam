"""Brake gauge widget - vertical bar showing brake application."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class BrakeIndicatorWidget(Widget):
    """Renders a vertical bar gauge for brake status, styled like TeslaClip BRK gauge."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        return ("brake", frame.brake_applied)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Label at top
        label_h = self.height // 5
        bar_top = label_h + 2
        bar_bottom = self.height - 2
        bar_h = bar_bottom - bar_top
        bar_x = 2
        bar_w = self.width - 4

        # Label "BRK"
        font_size = max(9, label_h - 2)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.truetype("FreeSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        label_color = self.theme.warning if frame.brake_applied else (180, 180, 180, 200)
        bbox = draw.textbbox((0, 0), "BRK", font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((self.width - tw) // 2, 0),
            "BRK",
            fill=label_color,
            font=font,
        )

        # Background track
        draw.rounded_rectangle(
            [bar_x, bar_top, bar_x + bar_w, bar_bottom],
            radius=3,
            fill=(40, 40, 40, 160),
            outline=(80, 80, 80, 140),
        )

        # Filled portion (from bottom up, full when braking)
        if frame.brake_applied:
            fill_color = (220, 40, 40, 240)
            draw.rounded_rectangle(
                [bar_x + 1, bar_top + 1, bar_x + bar_w - 1, bar_bottom - 1],
                radius=2,
                fill=fill_color,
            )

        return img
