from __future__ import annotations

from datetime import datetime, timezone
from typing import ItemsView

from .event import Event
from .video import Video_Metadata


class Movie(object):
    """Movie Class"""

    def __init__(self, filename: str | None = None):
        self._filename: str | None = filename
        self._start_timestamp: datetime | None = None
        self._end_timestamp: datetime | None = None
        self._duration: float | None = None
        self._events: dict[str, Event] = {}
        self._video_metadata: Video_Metadata | None = None

    @property
    def filename(self) -> str | None:
        return self._filename

    @filename.setter
    def filename(self, value: str):
        self._filename = value

    def event(self, folder: str) -> Event | None:
        return self._events.get(folder)

    def set_event(self, event_info: Event):
        key = event_info.folder if event_info.filename is None else event_info.filename
        self._events.update({key: event_info})

    def item(self, value: str) -> Event | None:
        return self.event(value)

    @property
    def first_item(self) -> Event | None:
        return self.event(self.sorted[0]) if self.sorted else None

    @property
    def items(self) -> ItemsView[str, Event]:
        return self._events.items()

    @property
    def items_sorted(self) -> list[Event]:
        return (
            [c for c in (self.event(event) for event in self.sorted) if c is not None]
            if len(self._events) > 0
            else []
        )

    @property
    def start_timestamp(self) -> datetime:
        if self._start_timestamp is not None:
            return self._start_timestamp

        if len(self.items) != 0 and (event := self.event(self.sorted[0])) is not None:
            return event.start_timestamp
        return datetime.now(timezone.utc)

    @start_timestamp.setter
    def start_timestamp(self, value: datetime) -> None:
        self._start_timestamp = value

    @property
    def end_timestamp(self) -> datetime:
        if self._end_timestamp is not None:
            return self._end_timestamp

        if len(self.items) == 0:
            return self.start_timestamp

        if (event := self.event(self.sorted[-1])) is not None:
            end_timestamp = event.end_timestamp

        for _, event_info in self.items:
            if event_info.end_timestamp > end_timestamp or end_timestamp is None:
                end_timestamp = event_info.end_timestamp
        return end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, value: datetime) -> None:
        self._end_timestamp = value

    @property
    def duration(self) -> float | None:
        return (
            (self.end_timestamp - self.start_timestamp).total_seconds()
            if self._duration is None
            else self._duration
        )

    @duration.setter
    def duration(self, value: float):
        self._duration = value

    @property
    def width(self) -> int | None:
        if self._video_metadata is not None:
            return self._video_metadata.width

        width = 0
        for item in self.items:
            video_metadata = item[1].video_metadata
            if video_metadata is not None:
                if (video_metadata.width or 0) > width:
                    width = video_metadata.width or 0

        return width

    @property
    def height(self) -> int | None:
        if self._video_metadata is not None:
            return self._video_metadata.height

        height = 0
        for item in self.items:
            video_metadata = item[1].video_metadata
            if video_metadata is not None:
                if (video_metadata.height or 0) > height:
                    height = video_metadata.height or 0
        return height

    @property
    def ratio(self) -> float:
        width = self.width or 0
        height = self.height or 0
        if width != 0 and height != 0:
            return width / height
        return 4 / 3

    @property
    def count(self) -> int:
        return len(self._events)

    @property
    def count_clips(self) -> int:
        count = 0
        for _, event_info in self.items:
            count = count + event_info.count
        return count

    @property
    def sorted(self) -> list[str]:
        return (
            sorted(self._events, key=lambda clip: self._events[clip].start_timestamp)
            if len(self._events) > 0
            else []
        )

    @property
    def video_metadata(self) -> Video_Metadata | None:
        return self._video_metadata

    @video_metadata.setter
    def video_metadata(self, value: Video_Metadata):
        self._video_metadata = value


__all__ = ["Movie"]
