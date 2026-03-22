"""G-force display widget with numeric value and directional bubble."""

import math

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme, get_font


class GForceDisplayWidget(Widget):
    """Renders G-force magnitude and a crosshair with directional dot."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        gx = round(frame.linear_acceleration_mps2_x / 9.81, 2)
        gy = round(frame.linear_acceleration_mps2_y / 9.81, 2)
        return ("gforce", gx, gy)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        gx = frame.linear_acceleration_mps2_x / 9.81
        gy = frame.linear_acceleration_mps2_y / 9.81
        magnitude = math.sqrt(gx * gx + gy * gy)

        # Layout: left side = text, right side = crosshair bubble
        bubble_size = min(self.height - 4, self.width // 2 - 4)
        text_w = self.width - bubble_size - 8

        # G-force text
        font_size = max(10, min(text_w // 3, self.height // 2 - 2))
        font = get_font(font_size, self.font_path)

        g_text = f"{magnitude:.2f}g"
        bbox = draw.textbbox((0, 0), g_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = max(0, (text_w - tw) // 2)
        ty = (self.height - th) // 2 - bbox[1]
        draw.text((tx, ty), g_text, fill=(220, 220, 220, 240), font=font)

        # Crosshair bubble on the right
        bcx = text_w + 4 + bubble_size // 2
        bcy = self.height // 2
        br = bubble_size // 2 - 2

        # Outer circle
        draw.ellipse(
            [bcx - br, bcy - br, bcx + br, bcy + br],
            outline=(100, 100, 100, 160),
            width=1,
        )

        # Crosshair lines
        draw.line([bcx - br, bcy, bcx + br, bcy], fill=(80, 80, 80, 120), width=1)
        draw.line([bcx, bcy - br, bcx, bcy + br], fill=(80, 80, 80, 120), width=1)

        # Force dot - clamp to circle radius
        max_g = 1.0  # 1g = edge of circle
        dot_x = int(bcx + (gx / max_g) * (br - 3))
        dot_y = int(bcy - (gy / max_g) * (br - 3))
        # Clamp to circle
        dx = dot_x - bcx
        dy = dot_y - bcy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > br - 3:
            scale = (br - 3) / dist
            dot_x = int(bcx + dx * scale)
            dot_y = int(bcy + dy * scale)

        dot_r = max(2, br // 5)
        # Color: green when low, yellow/red when high
        if magnitude < 0.3:
            dot_color = (100, 200, 100, 240)
        elif magnitude < 0.6:
            dot_color = (220, 200, 60, 240)
        else:
            dot_color = (220, 60, 60, 240)
        draw.ellipse(
            [dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
            fill=dot_color,
        )

        return img
