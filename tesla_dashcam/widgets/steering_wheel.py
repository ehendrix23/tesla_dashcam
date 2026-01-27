"""Steering wheel widget - rotates based on steering angle."""

import math

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme


class SteeringWheelWidget(Widget):
    """Renders a steering wheel that rotates with the steering angle."""

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
        rim_width = max(3 * scale, r // 8)
        spoke_width = max(2 * scale, r // 12)
        hub_r = r // 4

        # Outer rim
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=self.theme.primary,
            width=rim_width,
        )

        # Center hub
        draw.ellipse(
            [cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r],
            fill=self.theme.primary,
        )

        # Three spokes at 0, 135, 225 degrees (typical steering wheel)
        for angle_deg in [0, 135, 225]:
            rad = math.radians(angle_deg)
            inner_x = cx + int(hub_r * math.cos(rad))
            inner_y = cy + int(hub_r * math.sin(rad))
            outer_x = cx + int((r - rim_width // 2) * math.cos(rad))
            outer_y = cy + int((r - rim_width // 2) * math.sin(rad))
            draw.line(
                [inner_x, inner_y, outer_x, outer_y],
                fill=self.theme.primary,
                width=spoke_width,
            )

        # Rotate by steering angle (positive angle = clockwise turn)
        img = img.rotate(
            -frame.steering_wheel_angle,
            resample=Image.BICUBIC,
            center=(cx, cy),
        )

        # Downscale for antialiasing
        img = img.resize((self.width, self.height), Image.LANCZOS)
        return img
