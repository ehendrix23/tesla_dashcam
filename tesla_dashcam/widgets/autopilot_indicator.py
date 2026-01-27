"""Autopilot state indicator widget."""

import math

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class AutopilotIndicatorWidget(Widget):
    """Renders autopilot state badge: OFF, TACC, AP, or FSD with icon."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        return ("autopilot", frame.autopilot_state)

    def _get_label_and_color(self, frame):
        label = frame.autopilot_label
        if not label:
            return "OFF", (120, 120, 120, 180)
        if label == "FSD":
            return "FSD", (140, 80, 255, 255)
        if label == "AP":
            return "AP", (60, 140, 255, 255)
        if label == "TACC":
            return "TACC", (60, 140, 255, 255)
        return label, (120, 120, 120, 180)

    def _draw_bolt(self, draw, cx, cy, size, color):
        """Draw a small lightning bolt icon."""
        s = size / 2
        points = [
            (cx - s * 0.15, cy - s),
            (cx + s * 0.45, cy - s * 0.1),
            (cx + s * 0.05, cy - s * 0.1),
            (cx + s * 0.15, cy + s),
            (cx - s * 0.45, cy + s * 0.1),
            (cx - s * 0.05, cy + s * 0.1),
        ]
        draw.polygon(points, fill=color)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        label, color = self._get_label_and_color(frame)

        font_size = max(10, self.height - 6)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.truetype("FreeSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        # Draw bolt icon on the left
        bolt_size = min(self.height - 4, 16)
        bolt_cx = bolt_size // 2 + 2
        bolt_cy = self.height // 2
        self._draw_bolt(draw, bolt_cx, bolt_cy, bolt_size, color)

        # Draw label text
        text_x = bolt_size + 6
        bbox = draw.textbbox((0, 0), label, font=font)
        th = bbox[3] - bbox[1]
        ty = (self.height - th) // 2 - bbox[1]
        draw.text((text_x, ty), label, fill=color, font=font)

        return img
