from __future__ import annotations

from datetime import datetime, timezone
from typing import ItemsView, Optional

from tzlocal import get_localzone

from ..utils import get_current_timestamp
from .video import Clip, Video_Metadata


class Event_Metadata(object):
    def __init__(
        self,
        reason: Optional[str] = None,
        timestmp: Optional[datetime] = None,
        city: Optional[str] = None,
        street: Optional[str] = None,
        longitude: Optional[float] = None,
        latitude: Optional[float] = None,
    ) -> None:
        self._reason: Optional[str] = reason
        self._timestamp: Optional[datetime] = timestmp
        self._city: Optional[str] = city
        self._street: Optional[str] = street
        self._longitude: Optional[float] = longitude
        self._latitude: Optional[float] = latitude

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    @reason.setter
    def reason(self, value: str) -> None:
        self._reason = value

    @property
    def timestamp(self) -> Optional[datetime]:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime) -> None:
        self._timestamp = value

    @property
    def city(self) -> Optional[str]:
        return self._city

    @city.setter
    def city(self, value: str) -> None:
        self._city = value

    @property
    def street(self) -> Optional[str]:
        return self._street

    @street.setter
    def street(self, value: str) -> None:
        self._street = value

    @property
    def longitude(self) -> Optional[float]:
        return self._longitude

    @longitude.setter
    def longitude(self, value: float) -> None:
        self._longitude = value

    @property
    def latitude(self) -> Optional[float]:
        return self._latitude

    @latitude.setter
    def latitude(self, value: float) -> None:
        self._latitude = value


class Event(object):
    """Event Class"""

    def __init__(
        self,
        folder: str,
        isfile: bool = False,
        filename: Optional[str] = None,
        event_metadata: Optional[Event_Metadata] = None,
        video_metadata: Optional[Video_Metadata] = None,
    ):
        self._folder: str = folder
        self._isfile: bool = isfile
        self._filename: Optional[str] = filename
        self._event_metadata: Event_Metadata = (
            event_metadata if event_metadata else Event_Metadata()
        )
        self._video_metadata: Optional[Video_Metadata] = video_metadata
        self._start_timestamp: Optional[datetime] = None
        self._end_timestamp: Optional[datetime] = None
        self._duration: Optional[float] = None
        self._clips: dict[datetime, Clip] = {}
        self._camera_clips: list[str] = []

    @property
    def folder(self) -> str:
        return self._folder

    @property
    def timestamp(self) -> datetime:
        return self.start_timestamp

    @property
    def filename(self) -> Optional[str]:
        return self._filename

    @filename.setter
    def filename(self, value: str) -> None:
        self._filename = value

    @property
    def event_metadata(self) -> Event_Metadata:
        return self._event_metadata

    @property
    def video_metadata(self) -> Video_Metadata | None:
        return self._video_metadata

    @video_metadata.setter
    def video_metadata(self, value: Video_Metadata):
        self._video_metadata = value

    @property
    def isfile(self) -> bool:
        return self._isfile

    @isfile.setter
    def isfile(self, value: bool) -> None:
        self._isfile = value

    @property
    def width(self) -> int | None:
        if self._video_metadata is not None:
            return self._video_metadata.width

        width = 0
        for clip_item in self.items:
            video_metadata = clip_item[1].video_metadata
            if video_metadata is not None:
                if (video_metadata.width or 0) > width:
                    width = video_metadata.width or 0

        return width

    @property
    def height(self) -> int | None:
        if self._video_metadata is not None:
            return self._video_metadata.height

        height = 0
        for clip_item in self.items:
            video_metadata = clip_item[1].video_metadata
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

    def clip(self, timestmp: datetime) -> Clip | None:
        return self._clips.get(timestmp)

    def set_clip(self, timestmp: datetime, clip_info: Clip) -> None:
        self._clips.update({timestmp: clip_info})

    def has_camera_clip(self, camera: str) -> bool:
        """Returns the camera clips for the given camera."""
        return camera in self._camera_clips

    def add_camera_clip(self, camera: str):
        """Sets the camera clip for the given camera."""
        if camera not in self._camera_clips:
            self._camera_clips.append(camera)

    def item(self, value: datetime) -> Clip | None:
        return self.clip(value)

    @property
    def first_item(self) -> Clip | None:
        return self.clip(self.sorted[0]) if self.sorted else None

    @property
    def items(self) -> ItemsView[datetime, Clip]:
        return self._clips.items()

    @property
    def items_sorted(self) -> list[Clip]:
        return (
            [c for c in (self.clip(clip) for clip in self.sorted) if c is not None]
            if len(self._clips) > 0
            else []
        )

    @property
    def start_timestamp(self) -> datetime:
        if self._start_timestamp is not None:
            return self._start_timestamp

        if len(self.items) != 0 and (clip := self.clip(self.sorted[0])) is not None:
            return clip.start_timestamp
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

        if (clip := self.clip(self.sorted[-1])) is not None:
            end_timestamp = clip.end_timestamp

        for _, clip_info in self.items:
            if clip_info.end_timestamp > end_timestamp or end_timestamp is None:
                end_timestamp = clip_info.end_timestamp
        return end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, value: datetime) -> None:
        self._end_timestamp = value

    @property
    def duration(self) -> float:
        return (
            (self.end_timestamp - self.start_timestamp).total_seconds()
            if self._duration is None
            else self._duration
        )

    @duration.setter
    def duration(self, value: float) -> None:
        self._duration = value

    @property
    def count(self) -> int:
        return len(self._clips)

    @property
    def sorted(self) -> list[datetime]:
        return (
            sorted(self._clips, key=lambda clip: self._clips[clip].start_timestamp)
            if len(self._clips) > 0
            else []
        )

    def template(
        self, template: str | None, timestamp_format: str, video_settings: dict
    ) -> str:
        # This will also be called if no merging is going to occur (template = None) or
        # with an empty template (no grouping). In that case return "" as template.
        if template is None or template == "":
            return ""

        replacement_strings: dict[str, str] = {
            "layout": video_settings["movie_layout"],
            "start_timestamp": self.start_timestamp.astimezone(
                get_localzone()
            ).strftime(timestamp_format),
            "end_timestamp": self.end_timestamp.astimezone(get_localzone()).strftime(
                timestamp_format
            ),
            "event_timestamp": self.start_timestamp.astimezone(
                get_localzone()
            ).strftime(timestamp_format),
            "event_city": self.event_metadata.city or "",
            "event_street": self.event_metadata.street or "",
            "event_reason": self.event_metadata.reason or "",
            "event_latitude": str(self.event_metadata.latitude) or "",
            "event_longitude": str(self.event_metadata.longitude) or "",
        }

        if self.event_metadata.timestamp:
            replacement_strings["event_timestamp"] = (
                self.event_metadata.timestamp.astimezone(get_localzone()).strftime(
                    timestamp_format
                )
            )

        try:
            # Try to replace strings!
            template = template.format(**replacement_strings)
        except KeyError as e:
            print(
                f"{get_current_timestamp()}Bad string format for merge template: "
                f"Invalid variable {str(e)}"
            )
            template = ""

        if template == "":
            template = (
                f"{self.start_timestamp.astimezone(get_localzone()).strftime(timestamp_format)} - "
                f"{self.end_timestamp.astimezone(get_localzone()).strftime(timestamp_format)}"
            )
        return template


__all__ = ["Event", "Event_Metadata"]
