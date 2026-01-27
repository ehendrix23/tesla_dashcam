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
        # Render at 3x for smooth antialiasing, then downscale
        ss = 3
        size = self.width * ss
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        cx = cy = size // 2
        r = cx - 8 * ss
        rim_width = max(6 * ss, r // 4)  # thick rim for yoke look
        spoke_width = max(4 * ss, r // 5)
        hub_r = r // 4

        # Tesla yoke shape: two side grips with wide open top and bottom.
        # PIL arc angles: 0=3 o'clock, clockwise.
        # Left grip (9 o'clock area): 135 to 225 degrees
        # Right grip (3 o'clock area): -45 to 45 degrees
        bbox = [cx - r, cy - r, cx + r, cy + r]
        draw.arc(bbox, start=135, end=225, fill=self.theme.primary, width=rim_width)
        draw.arc(bbox, start=-45, end=45, fill=self.theme.primary, width=rim_width)

        # Rounded end caps at arc endpoints for polished look
        cap_r = rim_width // 2
        for angle in [135, 225, -45, 45]:
            rad = math.radians(angle)
            ex = cx + int(r * math.cos(rad))
            ey = cy + int(r * math.sin(rad))
            draw.ellipse(
                [ex - cap_r, ey - cap_r, ex + cap_r, ey + cap_r],
                fill=self.theme.primary,
            )

        # Horizontal crossbar connecting the two grips
        bar_left = cx - int(r * 0.72)
        bar_right = cx + int(r * 0.72)
        draw.line(
            [bar_left, cy, bar_right, cy],
            fill=self.theme.primary,
            width=spoke_width,
        )

        # Center hub (outer ring)
        draw.ellipse(
            [cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r],
            fill=self.theme.primary,
        )
        # Inner hub (darker center, Tesla logo area)
        inner_r = hub_r * 2 // 3
        draw.ellipse(
            [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
            fill=(40, 40, 40, 200),
        )

        # Rotate by steering angle
        img = img.rotate(
            -frame.steering_wheel_angle,
            resample=Image.BICUBIC,
            center=(cx, cy),
        )

        # Downscale for antialiasing
        img = img.resize((self.width, self.height), Image.LANCZOS)

        final = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        final.paste(img, (0, 0), img)

        return final
