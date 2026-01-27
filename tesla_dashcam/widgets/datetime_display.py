"""Date and time display widget with two-line layout."""

from datetime import datetime, timedelta
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

try:
    from tzlocal import get_localzone
except ImportError:
    get_localzone = None

from .base import Widget, WidgetTheme


class DateTimeDisplayWidget(Widget):
    """Renders date and time on a dark background panel.

    Two-line layout: smaller date on line 1, larger time on line 2.
    """

    def __init__(self, x, y, width, height, theme,
                 start_time: Optional[datetime] = None,
                 frame_rate: float = 36.0,
                 font_path=None):
        super().__init__(x, y, width, height, theme)
        self.start_time = start_time
        self.frame_rate = frame_rate
        self.font_path = font_path
        self._first_seq = None

    def _get_time(self, frame) -> Optional[datetime]:
        if self.start_time is None:
            return None
        if self._first_seq is None:
            self._first_seq = frame.frame_seq_no
        relative_frame = frame.frame_seq_no - self._first_seq
        offset = relative_frame / self.frame_rate
        t = self.start_time + timedelta(seconds=offset)
        if get_localzone is not None and t.tzinfo is not None:
            t = t.astimezone(get_localzone())
        return t

    def state_key(self, frame) -> tuple:
        t = self._get_time(frame)
        if t is None:
            return ("datetime", None)
        return ("datetime", t.strftime("%Y-%m-%d %H:%M:%S"))

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background panel
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=8,
            fill=(0, 0, 0, 170),
        )

        t = self._get_time(frame)
        if t is None:
            return img

        # Two-line layout: date (smaller) + time (larger)
        date_font_size = max(10, self.height // 3 - 2)
        time_font_size = max(12, self.height * 2 // 5)
        try:
            if self.font_path:
                date_font = ImageFont.truetype(self.font_path, date_font_size)
                time_font = ImageFont.truetype(self.font_path, time_font_size)
            else:
                date_font = ImageFont.truetype("FreeSans.ttf", date_font_size)
                time_font = ImageFont.truetype("FreeSans.ttf", time_font_size)
        except (OSError, IOError):
            date_font = ImageFont.load_default()
            time_font = date_font

        date_text = t.strftime("%a, %b %d, %Y")
        time_text = t.strftime("%H:%M:%S")

        # Date line (dimmer, smaller)
        pad = 8
        draw.text(
            (pad, 4), date_text,
            fill=(180, 180, 180, 200), font=date_font,
        )

        # Time line (bright, larger)
        date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
        date_h = date_bbox[3] - date_bbox[1]
        draw.text(
            (pad, 4 + date_h + 2), time_text,
            fill=(255, 255, 255, 245), font=time_font,
        )

        return img
