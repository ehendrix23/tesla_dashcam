"""Center cluster widget - composite panel with steering wheel, gauges, and G-force."""

import math

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme
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

        pad = 6
        ss = self.steering_size
        gw = self.gauge_w
        gh = self.gauge_h

        # Steering wheel centered at top of panel
        steer_x = (self.width - ss) // 2
        steer_y = pad
        steer_img = self._steering.render(frame)
        img.paste(steer_img, (steer_x, steer_y), steer_img)

        # Angle text below steering wheel
        angle = frame.steering_wheel_angle
        angle_text = f"{angle:+.0f}\u00b0"
        angle_font_size = max(10, ss // 5)
        try:
            if self.font_path:
                angle_font = ImageFont.truetype(self.font_path, angle_font_size)
            else:
                angle_font = ImageFont.truetype("FreeSans.ttf", angle_font_size)
        except (OSError, IOError):
            angle_font = ImageFont.load_default()

        angle_draw = ImageDraw.Draw(img)
        bbox = angle_draw.textbbox((0, 0), angle_text, font=angle_font)
        tw = bbox[2] - bbox[0]
        tx = (self.width - tw) // 2
        ty = steer_y + ss + 2
        angle_draw.text(
            (tx, ty), angle_text,
            fill=(220, 220, 220, 230), font=angle_font,
        )

        # Gauge row below angle text
        gauge_top = ty + angle_font_size + 6

        # ACC gauge on the left
        acc_x = self.width // 2 - gw - 8
        accel_img = self._accel.render(frame)
        # Resize gauge if needed
        if accel_img.size != (gw, gh):
            accel_img = accel_img.resize((gw, gh), Image.LANCZOS)
        img.paste(accel_img, (acc_x, gauge_top), accel_img)

        # BRK gauge on the right
        brk_x = self.width // 2 + 8
        brake_img = self._brake.render(frame)
        if brake_img.size != (gw, gh):
            brake_img = brake_img.resize((gw, gh), Image.LANCZOS)
        img.paste(brake_img, (brk_x, gauge_top), brake_img)

        # G-force display below gauges
        gforce_y = gauge_top + gh + 4
        gforce_h = max(20, self.height - gforce_y - pad)
        gforce_w = self.width - 2 * pad
        if gforce_h > 10:
            gforce = GForceDisplayWidget(
                0, 0, gforce_w, gforce_h, self.theme, font_path=self.font_path,
            )
            gforce_img = gforce.render(frame)
            img.paste(gforce_img, (pad, gforce_y), gforce_img)

        return img
