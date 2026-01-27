"""Date and time display widget."""

from datetime import datetime, timedelta
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

try:
    from tzlocal import get_localzone
except ImportError:
    get_localzone = None

from .base import Widget, WidgetTheme


class DateTimeDisplayWidget(Widget):
    """Renders the current date and time on a dark background panel."""

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
        # Track the first frame_seq_no to compute relative offsets
        if self._first_seq is None:
            self._first_seq = frame.frame_seq_no
        relative_frame = frame.frame_seq_no - self._first_seq
        offset = relative_frame / self.frame_rate
        t = self.start_time + timedelta(seconds=offset)
        # Convert to local timezone for display
        if get_localzone is not None and t.tzinfo is not None:
            t = t.astimezone(get_localzone())
        return t

    def state_key(self, frame) -> tuple:
        t = self._get_time(frame)
        if t is None:
            return ("datetime", None)
        # Update every second
        return ("datetime", t.strftime("%Y-%m-%d %H:%M:%S"))

    def render(self, frame) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background panel
        draw.rounded_rectangle(
            [0, 0, self.width - 1, self.height - 1],
            radius=6,
            fill=(0, 0, 0, 140),
        )

        t = self._get_time(frame)
        if t is None:
            return img

        font_size = max(10, self.height - 10)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.truetype("FreeSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        text = t.strftime("%b %d, %Y  %I:%M:%S %p")

        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (self.width - tw) // 2
        ty = (self.height - th) // 2 - bbox[1]
        draw.text((tx, ty), text, fill=(220, 220, 220, 240), font=font)

        return img
