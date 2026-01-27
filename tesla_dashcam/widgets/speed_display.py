"""Speed display widget - large readable speed with unit and optional autopilot badge."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class SpeedDisplayWidget(Widget):
    """Renders a large speed number with unit on a dark background panel.

    Optionally shows an autopilot state badge below the speed.
    """

    def __init__(self, x, y, width, height, theme,
                 speed_unit="mph", show_autopilot=False, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.speed_unit = speed_unit
        self.show_autopilot = show_autopilot
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        if self.speed_unit == "mph":
            speed_key = round(frame.speed_mph)
        elif self.speed_unit == "kmh":
            speed_key = round(frame.speed_kmh)
        else:
            speed_key = round(frame.vehicle_speed_mps, 1)
        ap_key = frame.autopilot_state if self.show_autopilot else None
        return ("speed", speed_key, ap_key)

    def _get_speed(self, frame):
        if self.speed_unit == "mph":
            return frame.speed_mph, "MPH"
        elif self.speed_unit == "kmh":
            return frame.speed_kmh, "KM/H"
        return frame.vehicle_speed_mps, "M/S"

    def _get_ap_label_color(self, frame):
        label = frame.autopilot_label
        if not label:
            return "OFF", (120, 120, 120, 160)
        if label == "FSD":
            return "FSD", (140, 80, 255, 240)
        if label in ("AP", "TACC"):
            return label, (60, 140, 255, 240)
        return label, (120, 120, 120, 160)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background panel
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=8,
            fill=(0, 0, 0, 170),
        )

        speed_val, unit_str = self._get_speed(frame)
        speed_text = f"{speed_val:.0f}"

        # Reserve space for AP badge if shown
        ap_height = self.height // 5 if self.show_autopilot else 0
        speed_area_h = self.height - ap_height

        # Load fonts
        big_size = speed_area_h * 3 // 5
        small_size = max(10, speed_area_h // 5)
        try:
            if self.font_path:
                big_font = ImageFont.truetype(self.font_path, big_size)
                small_font = ImageFont.truetype(self.font_path, small_size)
            else:
                big_font = ImageFont.truetype("FreeSans.ttf", big_size)
                small_font = ImageFont.truetype("FreeSans.ttf", small_size)
        except (OSError, IOError):
            big_font = ImageFont.load_default()
            small_font = big_font

        # Speed number - centered, large, bold white
        bbox = draw.textbbox((0, 0), speed_text, font=big_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (self.width - tw) // 2
        ty = (speed_area_h - th) // 2 - bbox[1] - small_size // 3
        draw.text(
            (tx, ty), speed_text,
            fill=(255, 255, 255, 255), font=big_font,
        )

        # Unit to the right of speed number, slightly smaller and dimmer
        bbox_u = draw.textbbox((0, 0), unit_str, font=small_font)
        uw = bbox_u[2] - bbox_u[0]
        ux = tx + tw + 4
        # If it overflows, center below instead
        if ux + uw > self.width - 4:
            ux = (self.width - uw) // 2
            uy = ty + th + 2
        else:
            uy = ty + th - (bbox_u[3] - bbox_u[1]) - 2
        draw.text(
            (ux, uy), unit_str,
            fill=(200, 200, 200, 220), font=small_font,
        )

        # Autopilot badge at bottom
        if self.show_autopilot:
            ap_label, ap_color = self._get_ap_label_color(frame)
            ap_font_size = max(9, ap_height - 4)
            try:
                if self.font_path:
                    ap_font = ImageFont.truetype(self.font_path, ap_font_size)
                else:
                    ap_font = ImageFont.truetype("FreeSans.ttf", ap_font_size)
            except (OSError, IOError):
                ap_font = ImageFont.load_default()

            # Lightning bolt + label
            bolt_text = "\u26a1 " + ap_label
            bp = draw.textbbox((0, 0), bolt_text, font=ap_font)
            bw = bp[2] - bp[0]
            bx = (self.width - bw) // 2
            by = speed_area_h
            draw.text((bx, by), bolt_text, fill=ap_color, font=ap_font)

        return img
