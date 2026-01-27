"""Gear state indicator widget."""

from PIL import Image, ImageDraw, ImageFont

from .base import Widget, WidgetTheme


class GearIndicatorWidget(Widget):
    """Renders P R N D with the active gear highlighted, on dark background."""

    def __init__(self, x, y, width, height, theme, font_path=None):
        super().__init__(x, y, width, height, theme)
        self.font_path = font_path

    def state_key(self, frame) -> tuple:
        return ("gear", frame.gear_state)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background panel
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=6,
            fill=(0, 0, 0, 140),
        )

        gears = ["P", "R", "N", "D"]
        active = frame.gear_letter

        font_size = min(self.height - 8, self.width // len(gears) - 4)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.truetype("FreeSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        slot_w = self.width // len(gears)
        for i, g in enumerate(gears):
            x = i * slot_w
            if g == active:
                color = (255, 255, 255, 255)
            else:
                color = (100, 100, 100, 160)

            bbox = draw.textbbox((0, 0), g, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = x + (slot_w - tw) // 2
            ty = (self.height - th) // 2 - bbox[1]
            draw.text((tx, ty), g, fill=color, font=font)

        return img
