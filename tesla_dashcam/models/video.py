from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import ItemsView, Optional


class Chapter(object):
    """Chapters Class"""

    def __init__(self, start=None, end=None, title=None) -> None:
        self._start: float | None = start
        self._end: float | None = end
        self._title: str | None = title

    @property
    def start(self) -> float | None:
        return self._start

    @start.setter
    def start(self, value: float):
        self._start = value

    @property
    def end(self) -> float | None:
        return self._end

    @end.setter
    def end(self, value: float):
        self._end = value

    @property
    def title(self) -> str | None:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value


class Video_Metadata(object):
    """Metadata Class"""

    def __init__(
        self,
        filename: str,
        timestp: datetime | None = None,
        duration: float = 0,
        include: bool = False,
        title: str | None = None,
        height: int | None = None,
        width: int | None = None,
        video_codec: str | None = None,
        fps: float | None = None,
        dar: str | None = None,
        chapters: list[Chapter] | None = None,
    ):
        self._filename: str = filename
        self._timestamp: datetime | None = timestp
        self._duration: float = duration
        self._include: bool = include
        self._title: str | None = title
        self._height: int | None = height
        self._width: int | None = width
        self._video_codec: str | None = video_codec
        self._fps: float | None = fps
        self._dar: str | None = dar
        self._chapters: list[Chapter] = chapters if chapters is not None else []

    @property
    def filename(self) -> str:
        return self._filename

    @filename.setter
    def filename(self, value: str):
        self._filename = value

    @property
    def timestamp(self) -> datetime | None:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime):
        self._timestamp = value

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, value: float):
        self._duration = value

    @property
    def include(self) -> bool:
        return self._include or True

    @include.setter
    def include(self, value: bool):
        self._include = value

    @property
    def title(self) -> str | None:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value

    @property
    def height(self) -> int | None:
        return self._height

    @height.setter
    def height(self, value: int):
        self._height = value

    @property
    def width(self) -> int | None:
        return self._width

    @width.setter
    def width(self, value: int):
        self._width = value

    @property
    def ratio(self) -> float:
        width = self.width or 0
        height = self.height or 0
        if width != 0 and height != 0:
            return width / height
        return 4 / 3

    @property
    def video_codec(self) -> str | None:
        return self._video_codec

    @video_codec.setter
    def video_codec(self, value: str):
        self._video_codec = value

    @property
    def fps(self) -> float | None:
        return self._fps

    @fps.setter
    def fps(self, value: float):
        self._fps = value

    @property
    def dar(self) -> str | None:
        return self._dar

    @dar.setter
    def dar(self, value: str):
        self._dar = value

    @property
    def chapters(self) -> list[Chapter] | None:
        return self._chapters

    @chapters.setter
    def chapters(self, value: list[Chapter]):
        self._chapters = value

    def add_chapter(self, chapter: Chapter):
        """Add a chapter to the metadata."""
        if chapter not in self._chapters:
            self._chapters.append(chapter)


class Camera_Clip(object):
    """Camera Clip Class"""

    def __init__(
        self,
        filename: str,
        timestmp: datetime,
        duration: float = 0,
        include: bool = False,
        video_metadata: Optional[Video_Metadata] = None,
    ) -> None:
        """Initialize the Camera Clip"""
        self._filename: str = filename
        self._timestamp: datetime = timestmp
        self._duration: float = duration
        self._include: bool = include
        self._video_metadata: Optional[Video_Metadata] = video_metadata

    @property
    def filename(self) -> str:
        return self._filename

    @filename.setter
    def filename(self, value: str) -> None:
        self._filename = value

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, value: float) -> None:
        self._duration = value

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime) -> None:
        self._timestamp = value

    @property
    def include(self) -> bool:
        return self._include

    @include.setter
    def include(self, value: bool) -> None:
        self._include = value

    @property
    def start_timestamp(self) -> datetime:
        return self.timestamp

    @property
    def end_timestamp(self) -> datetime:
        return self.start_timestamp + timedelta(seconds=self.duration)

    @property
    def video_metadata(self) -> Video_Metadata | None:
        return self._video_metadata

    @video_metadata.setter
    def video_metadata(self, value: Video_Metadata):
        self._video_metadata = value

    @property
    def width(self) -> int:
        if self._video_metadata is not None:
            return self._video_metadata.width or 0
        return 0

    @property
    def height(self) -> int:
        if self._video_metadata is not None:
            return self._video_metadata.height or 0
        return 0

    @property
    def ratio(self) -> float:
        if self.width != 0 and self.height != 0:
            return self.width / self.height
        return 4 / 3


class Clip(object):
    """Clip Class"""

    def __init__(self, timestmp: datetime, filename: Optional[str] = None) -> None:
        self._timestamp: datetime = timestmp
        self._filename: str | None = filename
        self._start_timestamp: datetime | None = None
        self._end_timestamp: datetime | None = None
        self._duration: float | None = None
        self._cameras: dict[str, Camera_Clip] = {}
        self._video_metadata: Video_Metadata | None = None

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def filename(self) -> str | None:
        return self._filename

    @filename.setter
    def filename(self, value: str) -> None:
        self._filename = value

    def camera(self, name: str) -> Camera_Clip | None:
        return self._cameras.get(name)

    def set_camera(self, name: str, camera_info: Camera_Clip) -> None:
        self._cameras.update({name: camera_info})

    @property
    def cameras(self) -> ItemsView[str, Camera_Clip]:
        return self._cameras.items()

    def item(self, value: str) -> Camera_Clip | None:
        return self.camera(value)

    @property
    def items(self) -> ItemsView[str, Camera_Clip]:
        return self.cameras

    @property
    def start_timestamp(self) -> datetime:
        if self._start_timestamp is not None:
            return self._start_timestamp
        if len(self.items) == 0:
            return datetime.now(timezone.utc)

        for camera in self.sorted:
            if (camera_clip := self.camera(camera)) is not None:
                if camera_clip.include:
                    return camera_clip.start_timestamp
        return self.timestamp

    @start_timestamp.setter
    def start_timestamp(self, value: datetime) -> None:
        self._start_timestamp = value

    @property
    def end_timestamp(self) -> datetime:
        if self._end_timestamp is not None:
            return self._end_timestamp

        if len(self.items) == 0:
            return self.start_timestamp

        end_timestamp = self.start_timestamp
        for _, camera_info in self.cameras:
            if camera_info.include:
                if end_timestamp is None:
                    end_timestamp = camera_info.end_timestamp
                else:
                    end_timestamp = (
                        camera_info.end_timestamp
                        if camera_info.end_timestamp > end_timestamp
                        else end_timestamp
                    )
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
    def sorted(self) -> list[str]:
        return sorted(
            self._cameras, key=lambda camera: self._cameras[camera].start_timestamp
        )

    @property
    def video_metadata(self) -> Video_Metadata | None:
        return self._video_metadata

    @video_metadata.setter
    def video_metadata(self, value: Video_Metadata):
        self._video_metadata = value

    @property
    def width(self) -> int:
        if self._video_metadata is not None:
            return self._video_metadata.width or 0
        return 0

    @property
    def height(self) -> int:
        if self._video_metadata is not None:
            return self._video_metadata.height or 0
        return 0

    @property
    def ratio(self) -> float:
        if self.width != 0 and self.height != 0:
            return self.width / self.height
        return 4 / 3


__all__ = ["Camera_Clip", "Chapter", "Clip", "Video_Metadata"]
