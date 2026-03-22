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
                 font_path=None, show_gforce=True):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path
        self.steering_size = steering_size
        self.gauge_w = gauge_w
        self.gauge_h = gauge_h
        self.show_gforce = show_gforce

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
        base = (
            "cluster",
            round(frame.steering_wheel_angle),
            round(frame.accelerator_pedal_position * 50),
            frame.brake_applied,
        )
        if self.show_gforce:
            gx = round(frame.linear_acceleration_mps2_x / 9.81, 2)
            gy = round(frame.linear_acceleration_mps2_y / 9.81, 2)
            return base + (gx, gy)
        return base

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
        angle_font_size = max(10, ss // 6)

        # Layout: steering wheel (+ angle text) on the left, gauges on the right
        # Gauge column sits to the right of the steering wheel
        gauge_gap = 8
        gauge_col_w = gw * 2 + gauge_gap + 12  # two bars + gap + labels
        steer_area_w = self.width - gauge_col_w - pad

        # Steering wheel centered in left area, vertically centered
        steer_x = max(pad, (steer_area_w - ss) // 2)
        steer_total_h = ss + angle_font_size + 2
        steer_y = max(pad, (self.height - steer_total_h) // 2)
        steer_img = self._steering.render(frame)
        img.paste(steer_img, (steer_x, steer_y), steer_img)

        # Angle text below steering wheel, centered under it
        angle = frame.steering_wheel_angle
        angle_text = f"{angle:+.0f}\u00b0"
        angle_font = get_font(angle_font_size, self.font_path)
        bbox = draw.textbbox((0, 0), angle_text, font=angle_font)
        tw = bbox[2] - bbox[0]
        tx = steer_x + (ss - tw) // 2
        ty = steer_y + ss
        draw.text(
            (tx, ty), angle_text,
            fill=(220, 220, 220, 230), font=angle_font,
        )

        # Gauge bars to the right of steering wheel, tall vertical bars
        # Draw labels above gauges in the cluster, then render gauge bars below
        gauge_x = steer_area_w
        label_font_size = max(10, self.height // 16)
        label_font = get_font(label_font_size, self.font_path)
        label_area_h = label_font_size + 4
        gauge_total_h = min(self.height - 2 * pad, int(self.height * 0.75))
        gh = gauge_total_h - label_area_h
        gauge_y = (self.height - gauge_total_h) // 2
        bar_y = gauge_y + label_area_h

        # ACC label
        acc_x = gauge_x
        has_input = frame.accelerator_pedal_position > 0.02
        acc_color = (80, 220, 80, 240) if has_input else (180, 180, 180, 200)
        acc_bbox = draw.textbbox((0, 0), "ACC", font=label_font)
        acc_tw = acc_bbox[2] - acc_bbox[0]
        draw.text(
            (acc_x + (gw - acc_tw) // 2, gauge_y),
            "ACC", fill=acc_color, font=label_font,
        )

        # BRK label
        brk_x = acc_x + gw + gauge_gap
        brk_color = self.theme.warning if frame.brake_applied else (180, 180, 180, 200)
        brk_bbox = draw.textbbox((0, 0), "BRK", font=label_font)
        brk_tw = brk_bbox[2] - brk_bbox[0]
        draw.text(
            (brk_x + (gw - brk_tw) // 2, gauge_y),
            "BRK", fill=brk_color, font=label_font,
        )

        # ACC gauge bar (render full widget, then crop off the label portion)
        accel_img = self._accel.render(frame)
        accel_label_h = accel_img.height // 5 + 2
        accel_bar = accel_img.crop((0, accel_label_h, accel_img.width, accel_img.height))
        bar_h = gh
        if accel_bar.size != (gw, bar_h):
            accel_bar = accel_bar.resize((gw, bar_h), Image.LANCZOS)
        img.paste(accel_bar, (acc_x, bar_y), accel_bar)

        # BRK gauge bar (same crop approach)
        brake_img = self._brake.render(frame)
        brake_label_h = brake_img.height // 5 + 2
        brake_bar = brake_img.crop((0, brake_label_h, brake_img.width, brake_img.height))
        if brake_bar.size != (gw, bar_h):
            brake_bar = brake_bar.resize((gw, bar_h), Image.LANCZOS)
        img.paste(brake_bar, (brk_x, bar_y), brake_bar)

        # G-force display below gauges (optional, for standalone overlay)
        if self.show_gforce:
            gforce_bottom = self.height - pad
            gforce_h = max(24, gforce_bottom - (gauge_y + gh) - 4)
            if gforce_h > 16:
                gforce_y = gauge_y + gh + 4
                gforce_w = self.width - 2 * pad
                gforce = GForceDisplayWidget(
                    0, 0, gforce_w, gforce_h, self.theme,
                    font_path=self.font_path,
                )
                gforce_img = gforce.render(frame)
                img.paste(gforce_img, (pad, gforce_y), gforce_img)

        return img
