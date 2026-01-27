"""Turn signal indicator widget - arrows that light up."""

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme


class TurnSignalWidget(Widget):
    """Renders left and right turn signal arrows."""

    def state_key(self, frame) -> tuple:
        return ("turn", frame.blinker_on_left, frame.blinker_on_right)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        gap = 6
        mid_y = self.height // 2

        # Constrain arrow dimensions to maintain aspect ratio.
        # Each arrow should be roughly 2:1 (width:height).
        max_arrow_w = (self.width - gap) // 2
        arrow_h = min(self.height, max_arrow_w)
        arrow_w = min(max_arrow_w, arrow_h * 2)

        # Center the arrows within the widget
        total_w = arrow_w * 2 + gap
        x_offset = (self.width - total_w) // 2
        y_offset = (self.height - arrow_h) // 2
        mid_y = y_offset + arrow_h // 2

        # Left arrow
        left_active = frame.blinker_on_left
        left_color = (0, 220, 0, 255) if left_active else (70, 70, 70, 120)
        shaft_h = arrow_h // 3
        head_w = arrow_w * 2 // 3

        lx = x_offset
        left_pts = [
            (lx, mid_y),
            (lx + head_w, y_offset + 1),
            (lx + head_w, mid_y - shaft_h // 2),
            (lx + arrow_w - 1, mid_y - shaft_h // 2),
            (lx + arrow_w - 1, mid_y + shaft_h // 2),
            (lx + head_w, mid_y + shaft_h // 2),
            (lx + head_w, y_offset + arrow_h - 1),
        ]
        draw.polygon(left_pts, fill=left_color)

        # Right arrow (mirrored)
        right_active = frame.blinker_on_right
        right_color = (0, 220, 0, 255) if right_active else (70, 70, 70, 120)
        rx = x_offset + arrow_w + gap

        right_pts = [
            (rx + arrow_w, mid_y),
            (rx + arrow_w - head_w, y_offset + 1),
            (rx + arrow_w - head_w, mid_y - shaft_h // 2),
            (rx + 1, mid_y - shaft_h // 2),
            (rx + 1, mid_y + shaft_h // 2),
            (rx + arrow_w - head_w, mid_y + shaft_h // 2),
            (rx + arrow_w - head_w, y_offset + arrow_h - 1),
        ]
        draw.polygon(right_pts, fill=right_color)

        return img
