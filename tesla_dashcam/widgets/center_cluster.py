"""Center cluster widget - composite panel with steering wheel, gauges, and G-force."""

import math

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme, get_font
from .steering_wheel import SteeringWheelWidget
from .accel_gauge import AccelGaugeWidget
from .brake_indicator import BrakeIndicatorWidget
from .gforce_display import GForceDisplayWidget


class CenterClusterWidget(Widget):
    """Composite widget: steering wheel + angle text + ACC/BRK gauges + G-force.

    Renders all sub-elements onto a shared dark semi-transparent panel.
    """

    def __init__(self, x, y, width, height, theme,
                 steering_size=90, gauge_w=28, gauge_h=70,
                 font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path
        self.steering_size = steering_size
        self.gauge_w = gauge_w
        self.gauge_h = gauge_h

        # Sub-widgets are rendered internally, not placed on the canvas
        self._steering = SteeringWheelWidget(
            0, 0, steering_size, steering_size, theme, font_path=font_path,
        )
        self._accel = AccelGaugeWidget(
            0, 0, gauge_w, gauge_h, theme, font_path=font_path,
        )
        self._brake = BrakeIndicatorWidget(
            0, 0, gauge_w, gauge_h, theme, font_path=font_path,
        )

    def state_key(self, frame) -> tuple:
        gx = round(frame.linear_acceleration_mps2_x / 9.81, 2)
        gy = round(frame.linear_acceleration_mps2_y / 9.81, 2)
        return (
            "cluster",
            round(frame.steering_wheel_angle),
            round(frame.accelerator_pedal_position * 50),
            frame.brake_applied,
            gx, gy,
        )

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark panel background
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=10,
            fill=(0, 0, 0, 170),
        )

        pad = 4
        ss = self.steering_size
        gw = self.gauge_w
        # Calculate available space for gauges and gforce
        angle_font_size = max(10, ss // 6)
        top_section = pad + ss + angle_font_size + 2  # steering + angle text
        remaining = self.height - top_section - pad
        # Split remaining between gauges (60%) and gforce (40%)
        gh = max(30, int(remaining * 0.55))
        gforce_h = max(24, remaining - gh - 4)

        # Steering wheel centered at top of panel
        steer_x = (self.width - ss) // 2
        steer_y = pad
        steer_img = self._steering.render(frame)
        img.paste(steer_img, (steer_x, steer_y), steer_img)

        # Angle text below steering wheel
        angle = frame.steering_wheel_angle
        angle_text = f"{angle:+.0f}\u00b0"
        angle_font = get_font(angle_font_size, self.font_path)

        bbox = draw.textbbox((0, 0), angle_text, font=angle_font)
        tw = bbox[2] - bbox[0]
        tx = (self.width - tw) // 2
        ty = steer_y + ss
        draw.text(
            (tx, ty), angle_text,
            fill=(220, 220, 220, 230), font=angle_font,
        )

        # Gauge row below angle text
        gauge_top = ty + angle_font_size + 2

        # ACC gauge on the left
        acc_x = self.width // 2 - gw - 6
        accel_img = self._accel.render(frame)
        if accel_img.size != (gw, gh):
            accel_img = accel_img.resize((gw, gh), Image.LANCZOS)
        img.paste(accel_img, (acc_x, gauge_top), accel_img)

        # BRK gauge on the right
        brk_x = self.width // 2 + 6
        brake_img = self._brake.render(frame)
        if brake_img.size != (gw, gh):
            brake_img = brake_img.resize((gw, gh), Image.LANCZOS)
        img.paste(brake_img, (brk_x, gauge_top), brake_img)

        # G-force display below gauges
        gforce_y = gauge_top + gh + 2
        gforce_w = self.width - 2 * pad
        if gforce_h > 16:
            gforce = GForceDisplayWidget(
                0, 0, gforce_w, gforce_h, self.theme, font_path=self.font_path,
            )
            gforce_img = gforce.render(frame)
            img.paste(gforce_img, (pad, gforce_y), gforce_img)

        return img
