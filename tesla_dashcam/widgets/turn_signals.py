"""Turn signal indicator widget."""

from PIL import Image, ImageDraw

from .base import Widget, WidgetTheme


class TurnSignalWidget(Widget):
    """Renders left and right turn signal arrows."""

    def state_key(self, frame) -> tuple:
        return ("turn", frame.blinker_on_left, frame.blinker_on_right)

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        arrow_w = self.width // 2 - 4
        arrow_h = self.height
        mid_y = self.height // 2

        # Left arrow
        left_color = self.theme.accent if frame.blinker_on_left else self.theme.inactive
        left_pts = [
            (0, mid_y),                          # left tip
            (arrow_w // 2, 2),                   # top
            (arrow_w // 2, arrow_h // 3),        # inner top
            (arrow_w, arrow_h // 3),             # right top
            (arrow_w, arrow_h * 2 // 3),         # right bottom
            (arrow_w // 2, arrow_h * 2 // 3),    # inner bottom
            (arrow_w // 2, arrow_h - 2),         # bottom
        ]
        draw.polygon(left_pts, fill=left_color)

        # Right arrow (mirrored)
        offset_x = self.width // 2 + 4
        right_color = self.theme.accent if frame.blinker_on_right else self.theme.inactive
        right_pts = [
            (offset_x + arrow_w, mid_y),                      # right tip
            (offset_x + arrow_w // 2, 2),                     # top
            (offset_x + arrow_w // 2, arrow_h // 3),          # inner top
            (offset_x, arrow_h // 3),                         # left top
            (offset_x, arrow_h * 2 // 3),                     # left bottom
            (offset_x + arrow_w // 2, arrow_h * 2 // 3),      # inner bottom
            (offset_x + arrow_w // 2, arrow_h - 2),           # bottom
        ]
        draw.polygon(right_pts, fill=right_color)

        return img
