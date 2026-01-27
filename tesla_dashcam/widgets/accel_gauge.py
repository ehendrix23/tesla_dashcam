"""Accelerator pedal gauge widget - vertical bar matching brake gauge style."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class AccelGaugeWidget(Widget):
    """Renders a vertical bar gauge showing accelerator pedal position."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        # Quantize to 2% steps
        return ("accel", round(frame.accelerator_pedal_position * 50))

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

        # Label "ACC"
        font_size = max(9, label_h - 2)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.truetype("FreeSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        has_input = frame.accelerator_pedal_position > 0.02
        label_color = (80, 220, 80, 240) if has_input else (180, 180, 180, 200)
        bbox = draw.textbbox((0, 0), "ACC", font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((self.width - tw) // 2, 0),
            "ACC",
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

        # Filled portion (from bottom up)
        fill_h = int(bar_h * frame.accelerator_pedal_position)
        if fill_h > 0:
            fill_top = bar_bottom - fill_h
            fill_color = (60, 200, 60, 230)
            draw.rounded_rectangle(
                [bar_x + 1, fill_top, bar_x + bar_w - 1, bar_bottom - 1],
                radius=2,
                fill=fill_color,
            )

        return img
