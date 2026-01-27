"""Longitudinal acceleration indicator widget.

Displays a tilt-style indicator showing forward/backward acceleration
(braking vs throttle), similar to an aircraft attitude indicator.
The horizon tilts based on longitudinal acceleration: braking tilts
forward (more ground visible), acceleration tilts backward (more sky).

Note: Tesla SEI telemetry provides linear_acceleration (gravity removed),
so this cannot represent road grade. Instead it shows dynamic
braking/acceleration force.
"""

import math

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme, get_font


class ElevationDisplayWidget(Widget):
    """Renders a tilt indicator from longitudinal acceleration data.

    Shows braking/acceleration as a tilting horizon: braking pitches
    the display forward (ground rises), throttle pitches backward
    (sky rises). Deceleration value shown as g-force to the right.
    """

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        ay = frame.linear_acceleration_mps2_y
        # Quantize to 0.1 m/s² steps
        ay_q = round(ay * 10) / 10
        return ("elevation", ay_q)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=6,
            fill=(0, 0, 0, 170),
        )

        # Longitudinal acceleration (y-axis): positive = forward accel,
        # negative = braking. Convert to g-force.
        ay = frame.linear_acceleration_mps2_y
        accel_g = ay / 9.81

        # Clamp for visual display: ±0.8g covers normal driving
        max_g = 0.8
        accel_clamped = max(-max_g, min(max_g, accel_g))

        # --- Attitude indicator (left side) ---
        indicator_size = min(self.height - 6, self.width // 2 - 4)
        ind_cx = 3 + indicator_size // 2
        ind_cy = self.height // 2
        ind_r = indicator_size // 2 - 1

        # Clip to circular region using a mask
        mask = Image.new("L", (self.width, self.height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse(
            [ind_cx - ind_r, ind_cy - ind_r, ind_cx + ind_r, ind_cy + ind_r],
            fill=255,
        )

        # Sky background (blue = coasting/neutral)
        sky_color = (70, 130, 200, 200)
        ground_color = (140, 100, 50, 200)
        draw.ellipse(
            [ind_cx - ind_r, ind_cy - ind_r, ind_cx + ind_r, ind_cy + ind_r],
            fill=sky_color,
        )

        # Horizon offset: braking (negative ay) = horizon rises (more ground)
        # acceleration (positive ay) = horizon drops (more sky)
        offset_y = int((accel_clamped / max_g) * ind_r * 0.7)

        hl_y = ind_cy - offset_y
        # Ground polygon: from horizon line down
        ground_pts = [
            (ind_cx - ind_r - 2, hl_y),
            (ind_cx + ind_r + 2, hl_y),
            (ind_cx + ind_r + 2, ind_cy + ind_r + 2),
            (ind_cx - ind_r - 2, ind_cy + ind_r + 2),
        ]
        ground_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        ground_draw = ImageDraw.Draw(ground_layer)
        ground_draw.polygon(ground_pts, fill=ground_color)
        ground_masked = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        ground_masked.paste(ground_layer, mask=mask)
        img = Image.alpha_composite(img, ground_masked)
        draw = ImageDraw.Draw(img)

        # Horizon line (white)
        draw.line(
            [ind_cx - ind_r, hl_y, ind_cx + ind_r, hl_y],
            fill=(255, 255, 255, 220),
            width=2,
        )

        # Reference crosshair at center (fixed)
        wing = ind_r // 3
        draw.line(
            [ind_cx - wing, ind_cy, ind_cx + wing, ind_cy],
            fill=(255, 200, 0, 240),
            width=2,
        )
        draw.ellipse(
            [ind_cx - 2, ind_cy - 2, ind_cx + 2, ind_cy + 2],
            fill=(255, 200, 0, 240),
        )

        # Outer ring
        draw.ellipse(
            [ind_cx - ind_r, ind_cy - ind_r, ind_cx + ind_r, ind_cy + ind_r],
            outline=(180, 180, 180, 200),
            width=2,
        )

        # --- Accel text (right side) ---
        text_x = 3 + indicator_size + 6
        font_size = max(9, self.height // 3)
        font = get_font(font_size, self.font_path)

        abs_g = abs(accel_g)
        if abs_g < 0.02:
            accel_text = "0.00g"
        elif accel_g > 0:
            accel_text = f"+{accel_g:.2f}g"
        else:
            accel_text = f"{accel_g:.2f}g"

        bbox = draw.textbbox((0, 0), accel_text, font=font)
        th = bbox[3] - bbox[1]
        ty = (self.height - th) // 2 - bbox[1]
        draw.text((text_x, ty), accel_text, fill=(220, 220, 220, 230), font=font)

        return img
