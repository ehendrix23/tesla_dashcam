"""Accelerator pedal gauge widget."""

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme


class AccelGaugeWidget(Widget):
    """Renders a horizontal bar gauge showing accelerator pedal position."""

    def state_key(self, frame) -> tuple:
        # Quantize to 2% steps
        return ("accel", round(frame.accelerator_pedal_position * 50))

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        border = 2
        bar_x = border
        bar_y = border
        bar_w = self.width - border * 2
        bar_h = self.height - border * 2

        # Background track
        draw.rounded_rectangle(
            [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
            radius=bar_h // 3,
            fill=self.theme.inactive,
        )

        # Filled portion
        fill_w = int(bar_w * frame.accelerator_pedal_position)
        if fill_w > 0:
            # Color gradient: green at low, yellow at mid, red near full
            pos = frame.accelerator_pedal_position
            if pos < 0.5:
                r = int(pos * 2 * 255)
                g = 200
            else:
                r = 255
                g = int((1.0 - pos) * 2 * 200)
            fill_color = (r, g, 0, 230)

            draw.rounded_rectangle(
                [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h],
                radius=bar_h // 3,
                fill=fill_color,
            )

        # Border outline
        draw.rounded_rectangle(
            [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
            radius=bar_h // 3,
            outline=self.theme.primary,
            width=border,
        )

        return img
