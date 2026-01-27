"""Attitude indicator (artificial horizon) widget derived from accelerometer data.

Displays road pitch as an aircraft-style attitude indicator with a tilting
horizon line separating sky (blue) and ground (brown), plus grade percentage.
"""

import math

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme, get_font


class ElevationDisplayWidget(Widget):
    """Renders an artificial horizon indicator from accelerometer data.

    The instrument shows a tilting horizon line with blue sky above and
    brown ground below, similar to an aircraft attitude indicator. The
    pitch angle is estimated from the z-axis and y-axis accelerometer
    readings. Grade percentage is shown to the right.
    """

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        az = frame.linear_acceleration_mps2_z
        ay = frame.linear_acceleration_mps2_y
        # Pitch angle from gravity components, quantized to 0.5 degree steps
        pitch = math.degrees(math.atan2(-ay, az))
        pitch_q = round(pitch * 2) / 2
        return ("elevation", pitch_q)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=6,
            fill=(0, 0, 0, 170),
        )

        az = frame.linear_acceleration_mps2_z
        ay = frame.linear_acceleration_mps2_y

        # Pitch angle: positive = nose up (uphill), negative = nose down
        pitch_rad = math.atan2(-ay, az)
        pitch_deg = math.degrees(pitch_rad)
        grade = math.tan(pitch_rad) * 100.0

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

        # Sky background (fill whole circle area with sky blue first)
        sky_color = (70, 130, 200, 200)
        ground_color = (140, 100, 50, 200)
        draw.ellipse(
            [ind_cx - ind_r, ind_cy - ind_r, ind_cx + ind_r, ind_cy + ind_r],
            fill=sky_color,
        )

        # Ground half: draw a tilted filled polygon below the horizon line
        # Pitch shifts the horizon up/down, clamped for visual range
        max_pitch_visual = 25.0  # degrees for full displacement
        pitch_clamped = max(-max_pitch_visual, min(max_pitch_visual, pitch_deg))
        # Horizon offset: positive pitch = horizon moves down (more sky)
        offset_y = int((pitch_clamped / max_pitch_visual) * ind_r * 0.8)

        # Tilted horizon line endpoints (roll would tilt it, but we only
        # have pitch data, so the line stays horizontal)
        hl_y = ind_cy - offset_y
        # Ground polygon: from horizon line down to bottom of circle
        ground_pts = [
            (ind_cx - ind_r - 2, hl_y),
            (ind_cx + ind_r + 2, hl_y),
            (ind_cx + ind_r + 2, ind_cy + ind_r + 2),
            (ind_cx - ind_r - 2, ind_cy + ind_r + 2),
        ]
        # Draw ground on a temp layer and composite with mask
        ground_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        ground_draw = ImageDraw.Draw(ground_layer)
        ground_draw.polygon(ground_pts, fill=ground_color)
        # Apply circular mask
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

        # Small aircraft/car reference symbol at center (fixed, doesn't move)
        wing = ind_r // 3
        draw.line(
            [ind_cx - wing, ind_cy, ind_cx + wing, ind_cy],
            fill=(255, 200, 0, 240),
            width=2,
        )
        # Center dot
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

        # --- Grade text (right side) ---
        text_x = 3 + indicator_size + 6
        font_size = max(9, self.height // 3)
        font = get_font(font_size, self.font_path)

        if grade >= 0.5:
            grade_text = f"+{grade:.1f}%"
        elif grade <= -0.5:
            grade_text = f"{grade:.1f}%"
        else:
            grade_text = "0.0%"

        bbox = draw.textbbox((0, 0), grade_text, font=font)
        th = bbox[3] - bbox[1]
        ty = (self.height - th) // 2 - bbox[1]
        draw.text((text_x, ty), grade_text, fill=(220, 220, 220, 230), font=font)

        return img
