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
        arrow_w = (self.width - gap) // 2
        arrow_h = self.height
        mid_y = self.height // 2

        # Left arrow
        left_active = frame.blinker_on_left
        left_color = (0, 220, 0, 255) if left_active else (70, 70, 70, 120)
        shaft_h = arrow_h // 3
        head_w = arrow_w * 2 // 3
        shaft_w = arrow_w - head_w

        # Left-pointing arrow
        left_pts = [
            (0, mid_y),                                # tip
            (head_w, 1),                               # top of head
            (head_w, mid_y - shaft_h // 2),            # inner top
            (arrow_w - 1, mid_y - shaft_h // 2),       # shaft top
            (arrow_w - 1, mid_y + shaft_h // 2),       # shaft bottom
            (head_w, mid_y + shaft_h // 2),            # inner bottom
            (head_w, arrow_h - 1),                     # bottom of head
        ]
        draw.polygon(left_pts, fill=left_color)

        # Right arrow (mirrored)
        right_active = frame.blinker_on_right
        right_color = (0, 220, 0, 255) if right_active else (70, 70, 70, 120)
        ox = arrow_w + gap

        right_pts = [
            (ox + arrow_w, mid_y),                         # tip
            (ox + arrow_w - head_w, 1),                    # top of head
            (ox + arrow_w - head_w, mid_y - shaft_h // 2), # inner top
            (ox + 1, mid_y - shaft_h // 2),                # shaft top
            (ox + 1, mid_y + shaft_h // 2),                # shaft bottom
            (ox + arrow_w - head_w, mid_y + shaft_h // 2), # inner bottom
            (ox + arrow_w - head_w, arrow_h - 1),          # bottom of head
        ]
        draw.polygon(right_pts, fill=right_color)

        return img
