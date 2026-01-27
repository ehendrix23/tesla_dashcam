"""Steering wheel widget - Tesla yoke style that rotates based on steering angle."""

import math

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class SteeringWheelWidget(Widget):
    """Renders a Tesla yoke-style steering wheel that rotates with the steering angle."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        return ("steering", round(frame.steering_wheel_angle))

    def render(self, frame) -> Image.Image:
        # Render at 2x for antialiasing, then downscale
        scale = 2
        size = self.width * scale
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        cx = cy = size // 2
        r = cx - 6 * scale
        rim_width = max(4 * scale, r // 6)
        spoke_width = max(3 * scale, r // 8)
        hub_r = r // 5

        # Tesla yoke: draw the rim as arcs (open top and bottom)
        # Left arc: from ~210 to ~330 degrees (bottom-left to top-left)
        # Right arc: from ~30 to ~150 degrees (top-right to bottom-right)
        # This creates the yoke shape with flat top and bottom

        # Draw left side arc
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.arc(bbox, start=150, end=250, fill=self.theme.primary, width=rim_width)
        # Draw right side arc
        draw.arc(bbox, start=-70, end=30, fill=self.theme.primary, width=rim_width)

        # Draw horizontal crossbar (connecting left and right at center)
        bar_y = cy
        bar_half = int(r * 0.65)
        draw.line(
            [cx - bar_half, bar_y, cx + bar_half, bar_y],
            fill=self.theme.primary,
            width=spoke_width,
        )

        # Small center hub/dot
        draw.ellipse(
            [cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r],
            fill=self.theme.primary,
        )

        # Left spoke (from hub to left arc)
        draw.line(
            [cx - hub_r, cy, cx - bar_half, cy],
            fill=self.theme.primary,
            width=spoke_width,
        )
        # Right spoke (from hub to right arc)
        draw.line(
            [cx + hub_r, cy, cx + bar_half, cy],
            fill=self.theme.primary,
            width=spoke_width,
        )

        # Rotate by steering angle
        img = img.rotate(
            -frame.steering_wheel_angle,
            resample=Image.BICUBIC,
            center=(cx, cy),
        )

        # Downscale for antialiasing
        img = img.resize((self.width, self.height), Image.LANCZOS)

        # Draw angle text below (not rotated)
        final = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        final.paste(img, (0, 0), img)

        return final
