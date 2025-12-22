"""
Merges the 3 Tesla Dashcam and Sentry camera video files into 1 video. If
then further concatenates the files together to make 1 movie.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from glob import glob, iglob
from inspect import isclass, isroutine
from pathlib import Path
from platform import processor as platform_processor
from re import IGNORECASE as re_IGNORECASE
from re import match, search
from shlex import split as shlex_split
from shutil import which
from subprocess import CalledProcessError, CompletedProcess, TimeoutExpired, run
from tempfile import mkstemp
from time import mktime, sleep
from time import time as timestamp
from types import SimpleNamespace
from typing import Any, ItemsView, Iterator, List, Optional

import requests
import staticmap
from dateutil.parser import isoparse
from PIL.Image import Image
from psutil import disk_partitions
from tzlocal import get_localzone

# Import on Windows only
# pylint: disable=import-error
if sys.platform == "win32":
    from win11toast import toast  # type: ignore[import]

_LOGGER = logging.getLogger(__name__)

# TODO: Move everything into classes and separate files. For example,
#  update class, font class (for timestamp), folder class, clip class (
#  combining front, left, and right info), file class (for individual file).
#  Clip class would then have to merge the camera clips, folder class would
#  have to concatenate the merged clips. Settings class to take in all settings
# TODO: Create kind of logger or output classes for output. That then allows
#  different ones to be created based on where it should go to (stdout,
#  log file, ...).

# cSpell: disable
VERSION = {"major": 0, "minor": 1, "patch": 21, "beta": 5}
VERSION_STR = f"v{VERSION['major']}.{VERSION['minor']}.{VERSION['patch']}"

if VERSION["beta"] > -1:
    VERSION_STR = f"{VERSION_STR}b{VERSION['beta']}"

MONITOR_SLEEP_TIME = 5

GITHUB = {
    "URL": "https://api.github.com",
    "owner": "ehendrix23",
    "repo": "tesla_dashcam",
}

FFMPEG = {
    "darwin": "ffmpeg",
    "win32": "ffmpeg.exe",
    "cygwin": "ffmpeg",
    "linux": "ffmpeg",
    "freebsd11": "ffmpeg",
}

MOVIE_HOMEDIR = {
    "darwin": "Movies/Tesla_Dashcam",
    "win32": r"Videos\Tesla_Dashcam",
    "cygwin": "Videos/Tesla_Dashcam",
    "linux": "Videos/Tesla_Dashcam",
    "freebsd11": "Videos/Tesla_Dashcam",
}

DEFAULT_CLIP_HEIGHT = 960
DEFAULT_CLIP_WIDTH = 1280
DEFAULT_FONT_HALIGN = "CENTER"
DEFAULT_FONT_VALIGN = "BOTTOM"

MOVIE_QUALITY = {
    "HIGH": "18",
    "MEDIUM": "20",
    "LOW": "23",
    "LOWER": "28",
    "LOWEST": "33",
}

MOVIE_ENCODING = {
    "x264": "libx264",
    "x264_nvidia": "h264_nvenc",
    "x264_mac": "h264_videotoolbox",
    "x264_intel": "h264_qsv",
    "x264_qsv": "h264_qsv",
    "x264_vaapi": "h264_vaapi",
    "x264_rpi": "h264_omx",
    "x265": "libx265",
    "x265_nvidia": "hevc_nvenc",
    "x265_mac": "hevc_videotoolbox",
    "x265_intel": "hevc_qsv",
    "x265_rpi": "h265",
}

DEFAULT_FONT = {
    "darwin": "/Library/Fonts/Arial Unicode.ttf",
    "win32": "/Windows/Fonts/arial.ttf",
    "cygwin": "/cygdrive/c/Windows/Fonts/arial.ttf",
    "linux": "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "freebsd11": "/usr/share/local/fonts/freefont-ttf/FreeSans.ttf",
}

HALIGN = {"LEFT": "10", "CENTER": "(w/2-text_w/2)", "RIGHT": "(w-text_w)"}

VALIGN = {"TOP": "10", "MIDDLE": "(h/2-(text_h/2))", "BOTTOM": "(h-(text_h)-10)"}

EVENT_REASON = {
    "sentry_aware_object_detection": "SENTRY",
    "sentry_aware_accel*": "SENTRY",
    "user_interaction_dashcam_icon_tapped": "SAVED",
    "user_interaction_honk": "HONK",
    "sentry_aware*": "SENTRY",
    "user_interaction*": "USER",
}

FFMPEG_LEFT_PERSPECTIVE = (
    ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000, "
    "perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:"
    "x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination"
)

FFMPEG_RIGHT_PERSPECTIVE = (
    ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000,"
    "perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:"
    "x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination"
)


FFMPEG_DEBUG = False
DISPLAY_TS = False

PLATFORM = sys.platform
# Allow setting for testing.
# PLATFORM = "darwin"
# PLATFORM = "win32"
# PLATFORM = "linux"

# cSpell: enable

PROCESSOR = platform_processor()
if PLATFORM == "darwin" and PROCESSOR == "i386":
    try:
        sysctl = run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            timeout=120,
            text=True,
            check=True,
        )
    except TimeoutExpired:
        print("Timeout running sysctl")
    except CalledProcessError as exc:
        _LOGGER.error("Error running sysctl: %d - %s", exc.returncode, exc.stderr)
    else:
        if search("Apple", sysctl.stdout, re_IGNORECASE) is not None:
            PROCESSOR = "arm"

# Allow setting for testing.
# PROCESSOR = "arm"


class Chapter(object):
    """Chapters Class"""

    def __init__(self, start=None, end=None, title=None):
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
                f"{
                    self.start_timestamp.astimezone(get_localzone()).strftime(
                        timestamp_format
                    )
                } - "
                f"{
                    self.end_timestamp.astimezone(get_localzone()).strftime(
                        timestamp_format
                    )
                }"
            )
        return template


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


class Font(object):
    """Font Class"""

    def __init__(
        self,
        layout: MovieLayout,
        font: str | None = None,
        size: int | None = None,
        color: str | None = None,
    ):
        self._layout: MovieLayout = layout
        self._font: str | None = font or DEFAULT_FONT.get(PLATFORM, None)
        self._size: int | None = size
        self._color: str | None = color
        self._halign: str = DEFAULT_FONT_HALIGN
        self._valign: str = DEFAULT_FONT_VALIGN
        self._xpos: int | None = None
        self._ypos: int | None = None

    @property
    def font(self) -> str | None:
        return self._font

    @font.setter
    def font(self, value: str) -> None:
        self._font = value

    @property
    def size(self) -> int:
        if (overriden := self._get_overridden("font_size")) is not None:
            return int(overriden)

        return (
            int(max(16, 16 * self._layout.scale)) if self._size is None else self._size
        )

    @size.setter
    def size(self, value: int) -> None:
        self._size = value

    @property
    def color(self) -> str | None:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        self._color = value

    @property
    def halign(self) -> str:
        if (overriden := self._get_overridden("font_halign")) is not None:
            return str(overriden)

        return HALIGN.get(self._halign, HALIGN[DEFAULT_FONT_HALIGN])

    @halign.setter
    def halign(self, value: str) -> None:
        self._halign = value

    @property
    def valign(self) -> str:
        if (overriden := self._get_overridden("font_valign")) is not None:
            return str(overriden)
        return VALIGN.get(self._valign, VALIGN[DEFAULT_FONT_VALIGN])

    @valign.setter
    def valign(self, value: str) -> None:
        self._valign = value

    @property
    def xpos(self) -> int | None:
        return self._xpos

    @xpos.setter
    def xpos(self, value: int | None) -> None:
        self._xpos = value

    @property
    def ypos(self) -> int | None:
        return self._ypos

    @ypos.setter
    def ypos(self, value: int | None) -> None:
        self._ypos = value

    def _get_overridden(self, attr) -> str | int | None:
        try:
            return getattr(self._layout, f"{attr}", None)()  # type: ignore[misc]
        except (AttributeError, TypeError):
            return None


class Camera(object):
    """Camera Class"""

    def __init__(self, layout: MovieLayout, camera: str):
        self._layout: MovieLayout = layout
        self._camera: str = camera
        self._include: bool = True
        self._width: int = 1280
        self._height: int = 960
        self._clip_ratio: float = 4 / 3
        self._xpos: int = 0
        self._xpos_override: bool = False
        self._ypos: int = 0
        self._ypos_override: bool = False
        self._scale: float | None = 1
        self._mirror: bool = False
        self._options: str = ""

    @property
    def layout(self) -> MovieLayout:
        return self._layout

    @layout.setter
    def layout(self, value: MovieLayout) -> None:
        self._layout = value

    @property
    def camera(self) -> str:
        return self._camera

    @camera.setter
    def camera(self, value: str) -> None:
        self._camera = value

    @property
    def include(self) -> bool:
        # If we're supposed to include then check the event to see if it should be
        # included
        if not self._include:
            return False

        # Make sure layout has an event.
        if self._layout.event is not None:
            return self._layout.event.has_camera_clip(self.camera)

        return self._include

    @include.setter
    def include(self, value: bool) -> None:
        self._include = value

    @property
    def width_fixed(self) -> int:
        return self._width

    @property
    def height_fixed(self) -> int:
        return self._height

    @property
    def width(self) -> int:
        if (overriden := self._get_overridden("width")) is not None:
            return int(overriden) * self.include

        return int(self._width * (self.scale or 1)) * self.include

    @width.setter
    def width(self, value: int) -> None:
        self._width = value

    @property
    def scale_width(self) -> int:
        return self.width

    @property
    def height(self) -> int:
        perspective_adjustement: float = 1
        if self.layout.perspective and self.camera in [
            "left",
            "right",
            "left_pillar",
            "right_pillar",
        ]:
            # Adjust height for perspective cameras
            perspective_adjustement = 3 / 2
        return int(self.scale_height * perspective_adjustement)

    @height.setter
    def height(self, value: int) -> None:
        self._height = value

    @property
    def scale_height(self) -> int:
        if (overriden := self._get_overridden("height")) is not None:
            return int(overriden) * self.include

        return int(self._height * (self.scale or 1)) * self.include

    @property
    def ratio(self) -> float:
        width = self.width_fixed or 0
        height = self.height_fixed or 0
        if width != 0 and height != 0:
            return width / height
        return 4 / 3

    @property
    def clip_ratio(self) -> float:
        return self._clip_ratio or 4 / 3

    @clip_ratio.setter
    def clip_ratio(self, value: float) -> None:
        self._clip_ratio = value

    @property
    def xpos(self) -> int:
        if not self._xpos_override:
            if (overriden := self._get_overridden("xpos")) is not None:
                return int(overriden) * self.include
        return self._xpos * self.include

    @xpos.setter
    def xpos(self, value: int) -> None:
        if value is not None:
            self._xpos = int(value)
            self._xpos_override = True
        else:
            self._xpos_override = False

    @property
    def ypos(self) -> int:
        if not self._ypos_override:
            override = self._get_overridden("ypos")
            if override is not None:
                return int(override) * self.include
        return self._ypos * self.include

    @ypos.setter
    def ypos(self, value: int) -> None:
        if value is not None:
            self._ypos = int(value)
            self._ypos_override = True
        else:
            self._ypos_override = False

    @property
    def scale(self) -> float | None:
        return self._scale

    @scale.setter
    def scale(self, value: float | None) -> None:
        if value is None:
            self._scale = None
        elif len(str(value).split("x")) == 1:
            # Scale provided is a multiplier
            self._scale = float(str(value).split("x")[0])
        else:
            # Scale is a resolution.
            parts = str(value).split("x")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(
                    f"Invalid resolution format: '{value}'. Expected format: "
                    "WIDTHxHEIGHT (e.g., 1920x1080)"
                )
            self.width = int(parts[0])
            self.height = int(parts[1])
            self._scale = 1

    @property
    def options(self) -> str:
        return self._options

    @options.setter
    def options(self, value: str):
        self._options = value

    @property
    def mirror(self) -> bool:
        return self._mirror

    @mirror.setter
    def mirror(self, value: bool) -> None:
        self._mirror = value

    @property
    def mirror_text(self) -> str | None:
        return ", hflip" if self.mirror else ""

    def _get_overridden(self, attr) -> str | int | None:
        try:
            attr_func = getattr(self._layout, f"{self.camera}_{attr}", None)
            return attr_func() if attr_func is not None else None  # type: ignore[misc]
        except (AttributeError, TypeError):
            return None


class MovieLayout(object):
    """Main Layout class"""

    def __init__(self) -> None:
        self._cameras: dict[str, Camera] = {
            "front": Camera(layout=self, camera="front"),
            "left": Camera(layout=self, camera="left"),
            "right": Camera(layout=self, camera="right"),
            "rear": Camera(layout=self, camera="rear"),
            "left_pillar": Camera(layout=self, camera="left_pillar"),
            "right_pillar": Camera(layout=self, camera="right_pillar"),
        }
        self._clip_order: list[str] = [
            "left",
            "right",
            "front",
            "rear",
            "left_pillar",
            "right_pillar",
        ]
        self._font: Font = Font(layout=self)

        self._swap_left_right: bool = False
        self._swap_front_rear: bool = False
        self._swap_pillar: bool = False

        self._perspective: bool = False
        self._title_screen_map: bool = False
        self._event: Event | None = None

        self.background_color = "black"
        self._font.halign = "CENTER"
        self._font.valign = "BOTTOM"

    def cameras(self, camera: str) -> Camera:
        return self._cameras[camera]

    @property
    def clip_order(self) -> list[str]:
        return self._clip_order

    @clip_order.setter
    def clip_order(self, value: list[str]) -> None:
        self._clip_order = []
        for camera in value:
            camera = camera.lower().strip()
            if camera in [
                "front",
                "left",
                "right",
                "rear",
                "left_pillar",
                "right_pillar",
            ]:
                self._clip_order.append(camera)

        # Make sure we have all of them, if not then add based on default order.
        if "left" not in self._clip_order:
            self._clip_order.append("left")
        if "right" not in self._clip_order:
            self._clip_order.append("right")
        if "front" not in self._clip_order:
            self._clip_order.append("front")
        if "rear" not in self._clip_order:
            self._clip_order.append("rear")
        if "left_pillar" not in self._clip_order:
            self._clip_order.append("left_pillar")
        if "right_pillar" not in self._clip_order:
            self._clip_order.append("right_pillar")

    @property
    def font(self) -> Font:
        return self._font

    @font.setter
    def font(self, value: Font) -> None:
        self._font = value

    @property
    def swap_left_right(self) -> bool:
        return self._swap_left_right

    @swap_left_right.setter
    def swap_left_right(self, value: bool) -> None:
        self._swap_left_right = value

    @property
    def swap_front_rear(self) -> bool:
        return self._swap_front_rear

    @swap_front_rear.setter
    def swap_front_rear(self, value: bool) -> None:
        self._swap_front_rear = value

    @property
    def swap_pillar(self) -> bool:
        return self._swap_pillar

    @swap_pillar.setter
    def swap_pillar(self, value: bool) -> None:
        self._swap_pillar = value

    @property
    def perspective(self) -> bool:
        return self._perspective

    @perspective.setter
    def perspective(self, new_perspective: bool) -> None:
        self._perspective = new_perspective

        if self._perspective:
            self.cameras("left").options = FFMPEG_LEFT_PERSPECTIVE
            self.cameras("right").options = FFMPEG_RIGHT_PERSPECTIVE
            self.cameras("left_pillar").options = FFMPEG_LEFT_PERSPECTIVE
            self.cameras("right_pillar").options = FFMPEG_RIGHT_PERSPECTIVE
        else:
            self.cameras("left").options = ""
            self.cameras("right").options = ""
            self.cameras("left_pillar").options = ""
            self.cameras("right_pillar").options = ""

    @property
    def scale(self) -> float:
        # Return scale of new video based on 1280x960 video = scale:1
        return (self.video_height * self.video_width) / (1280 * 960)

    @scale.setter
    def scale(self, scale: float) -> None:
        self.cameras("front").scale = scale
        self.cameras("left").scale = scale
        self.cameras("right").scale = scale
        self.cameras("rear").scale = scale
        self.cameras("left_pillar").scale = scale
        self.cameras("right_pillar").scale = scale

    @property
    def event(self) -> Event | None:
        return self._event

    @event.setter
    def event(self, value: Event) -> None:
        self._event = value

    @property
    def title_screen_map(self) -> bool:
        return self._title_screen_map

    @title_screen_map.setter
    def title_screen_map(self, value: bool):
        self._title_screen_map = value

    @property
    def video_width(self) -> int:
        return int(
            max(
                self.cameras("front").xpos + self.cameras("front").width,
                self.cameras("right").xpos + self.cameras("right").width,
                self.cameras("left_pillar").xpos + self.cameras("left_pillar").width,
                self.cameras("right_pillar").xpos + self.cameras("right_pillar").width,
                self.cameras("left").xpos + self.cameras("left").width,
                self.cameras("rear").xpos + self.cameras("rear").width,
            )
        )

    @property
    def video_height(self) -> int:
        return int(
            max(
                self.cameras("front").ypos + self.cameras("front").height,
                self.cameras("rear").ypos + self.cameras("rear").height,
                self.cameras("left_pillar").ypos + self.cameras("left_pillar").height,
                self.cameras("right_pillar").ypos + self.cameras("right_pillar").height,
                self.cameras("left").ypos + self.cameras("left").height,
                self.cameras("right").ypos + self.cameras("right").height,
            )
        )

    @property
    def center_xpos(self) -> int:
        return int(self.video_width / 2)

    @property
    def center_ypos(self) -> int:
        return int(self.video_height / 2)

    def rear_xpos(self) -> int:
        return self.cameras("front").xpos + self.cameras("front").width

    def left_pillar_ypos(self) -> int:
        return max(
            self.cameras("front").ypos + self.cameras("front").height,
            self.cameras("rear").ypos + self.cameras("rear").height,
        )

    def right_pillar_xpos(self) -> int:
        return self.cameras("left_pillar").xpos + self.cameras("left_pillar").width

    def right_pillar_ypos(self) -> int:
        return self.cameras("left_pillar").ypos

    def left_ypos(self) -> int:
        return max(
            self.cameras("front").ypos + self.cameras("front").height,
            self.cameras("rear").ypos + self.cameras("rear").height,
            self.cameras("left_pillar").ypos + self.cameras("left_pillar").height,
            self.cameras("right_pillar").ypos + self.cameras("right_pillar").height,
        )

    def right_xpos(self) -> int:
        return self.cameras("left").xpos + self.cameras("left").width

    def right_ypos(self) -> int:
        return self.cameras("left").ypos


class FullScreen(MovieLayout):
    """FullScreen Movie Layout

    [LEFT-PILLAR_CAMERA][FRONT_CAMERA][RIGHT-PILLAR_CAMERA]
    [   LEFT_CAMERA    ][REAR_CAMERA ][   RIGHT_CAMERA    ]
    """

    def __init__(self) -> None:
        super().__init__()
        self.scale = 1 / 2

    @property
    def _top_row_width(self) -> int:
        return (
            self.cameras("left_pillar").width
            + self.cameras("front").width
            + self.cameras("right_pillar").width
        )

    @property
    def _bottom_row_width(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("rear").width
            + self.cameras("right").width
        )

    @property
    def _row_width(self) -> int:
        # Use the maximum of the top and bottom row width.
        return max(self._top_row_width, self._bottom_row_width)

    @property
    def _top_row_xpos(self) -> int:
        # Make sure that top row is centered.
        return int(self._row_width / 2) - int(self._top_row_width / 2)

    @property
    def _bottom_row_xpos(self) -> int:
        # Make sure that bottom row is centered.
        return int(self._row_width / 2) - int(self._bottom_row_width / 2)

    @property
    def _top_row_height(self) -> int:
        return max(
            self.cameras("left_pillar").height,
            self.cameras("front").height,
            self.cameras("right_pillar").height,
        )

    @property
    def _bottom_row_height(self) -> int:
        return max(
            self.cameras("left").height,
            self.cameras("rear").height,
            self.cameras("right").height,
        )

    @property
    def _row_height(self) -> int:
        # Use the maximum of the top and bottom row height.
        return self._top_row_height + self._bottom_row_height

    @property
    def _top_row_ypos(self) -> int:
        # Make sure that top row is centered.
        return 0

    @property
    def _bottom_row_ypos(self) -> int:
        # Make sure that bottom row is centered.
        return self._top_row_height

    # We can't use video width or center_xpos as they use the positions to calculate.
    def left_pillar_xpos(self) -> int:
        # left_pillar is put on the left but ensuring that the row is centered
        return self._top_row_xpos

    def front_xpos(self) -> int:
        # front is placed next to left_pillar, we need to use width as left pillar
        # might not be included
        return self._top_row_xpos + self.cameras("left_pillar").width

    def right_pillar_xpos(self) -> int:
        # right_pillar is placed next to front, we need to use width as left pillar or
        # front might not be included
        return (
            self._top_row_xpos
            + self.cameras("left_pillar").width
            + self.cameras("front").width
        )

    # We can't use video width or center_xpos as they use the positions to calculate.
    def left_xpos(self) -> int:
        # left is put on the left but ensuring that the row is centered
        return self._bottom_row_xpos

    def rear_xpos(self) -> int:
        # rear is placed next to left, we need to use width as left might not be
        # included
        return self._bottom_row_xpos + self.cameras("left").width

    def right_xpos(self) -> int:
        # right is placed next to rear, we need to use width as left and rear might not
        # be included
        return (
            self._bottom_row_xpos
            + self.cameras("left").width
            + self.cameras("rear").width
        )

    def front_height(self) -> int:
        # For height keep same ratio as original clip
        return int(self.cameras("front").width / self.cameras("front").ratio)

    def left_pillar_ypos(self) -> int:
        return self._top_row_ypos + int(
            (self._top_row_height - self.cameras("left_pillar").height) / 2
        )

    def front_ypos(self) -> int:
        return self._top_row_ypos + int(
            (self._top_row_height - self.cameras("front").height) / 2
        )

    def right_pillar_ypos(self) -> int:
        return self._top_row_ypos + int(
            (self._top_row_height - self.cameras("right_pillar").height) / 2
        )

    def left_ypos(self) -> int:
        return self._bottom_row_ypos + int(
            (self._bottom_row_height - self.cameras("left").height) / 2
        )

    def rear_ypos(self) -> int:
        return self._bottom_row_ypos + int(
            (self._bottom_row_height - self.cameras("rear").height) / 2
        )

    def right_ypos(self) -> int:
        return self._bottom_row_ypos + int(
            (self._bottom_row_height - self.cameras("right").height) / 2
        )


class Mosaic(FullScreen):
    """Mosaic Movie Layout

    [LEFT-PILLAR_CAMERA][           FRONT_CAMERA             ][RIGHT-PILLAR_CAMERA]
    [       LEFT_CAMERA        ][    REAR_CAMERA     ][       RIGHT_CAMERA        ]

    or

    [LEFT-PILLAR_CAMERA][FRONT_CAMERA][RIGHT-PILLAR_CAMERA]
    [LEFT_CAMERA][       REAR_CAMERA        ][RIGHT_CAMERA]
    """

    def __init__(self) -> None:
        """Initialize Mosaic Layout."""
        super().__init__()
        self.scale = 1 / 2
        # Set front scale to None so we know if it was overriden or not.
        self.cameras("front").scale = None
        self.cameras("rear").scale = None
        # Boost factor to emphasize front/rear when pillars and sides present
        self._front_rear_boost: float = 1.3

    @property
    def front_rear_boost(self) -> float:
        return self._front_rear_boost

    @front_rear_boost.setter
    def front_rear_boost(self, value: float) -> None:
        self._front_rear_boost = max(1.0, float(value))

    def _boost_active(self) -> bool:
        # Always apply boost to keep front/rear emphasized consistently
        return True

    @property
    def _front_normal_scale(self) -> int:
        scale = self.cameras("front").scale or 0.5
        return int(self.cameras("front").width_fixed * scale)

    @property
    def _min_top_row_width(self) -> int:
        return (
            self.cameras("left_pillar").width
            + self._front_normal_scale
            + self.cameras("right_pillar").width
        )

    @property
    def _rear_normal_scale(self) -> int:
        scale = self.cameras("rear").scale or 0.5
        return int(self.cameras("rear").width_fixed * scale)

    @property
    def _min_bottom_row_width(self) -> int:
        return int(
            self.cameras("left").width
            + self._rear_normal_scale
            + self.cameras("right").width
        )

    # Adjust front width if bottom row is wider then top row
    def front_width(self) -> int:
        if self.cameras("front").scale is None:
            # Front width should be:
            #  max(bottom_row_width, min_top_width) - pillar_widths
            base_target = max(self._min_bottom_row_width, self._min_top_row_width)
            target_width = (
                int(base_target * self._front_rear_boost)
                if self._boost_active()
                else base_target
            )
            return max(
                self._front_normal_scale,
                target_width
                - self.cameras("left_pillar").width
                - self.cameras("right_pillar").width,
            )
        else:
            # Use normal scale calculation if front camera scale was explicitly set
            return self._front_normal_scale

    def front_height(self) -> int:
        # Preserve aspect ratio: if width is dynamically set (scale None),
        # derive height from width and clip ratio.
        if self.cameras("front").scale is None:
            return int(self.cameras("front").width / self.cameras("front").ratio)
        # Otherwise use explicit scale on original height.
        scale = self.cameras("front").scale or 1
        return int(self.cameras("front").height_fixed * scale)

    # Adjust rear width if bottom row is wider then top row
    def rear_width(self) -> int:
        if self.cameras("rear").scale is None:
            # Rear width should be:
            #  max(bottom_row_width, min_top_width) - left/right widths
            base_target = max(self._min_bottom_row_width, self._min_top_row_width)
            target_width = (
                int(base_target * self._front_rear_boost)
                if self._boost_active()
                else base_target
            )
            return max(
                self._rear_normal_scale,
                target_width - self.cameras("left").width - self.cameras("right").width,
            )
        else:
            # Use normal scale calculation if front camera scale was explicitly set
            return self._rear_normal_scale

    def rear_height(self) -> int:
        # Preserve aspect ratio: if width is dynamically set (scale None),
        # derive height from width and clip ratio.
        if self.cameras("rear").scale is None:
            return int(self.cameras("rear").width / self.cameras("rear").ratio)
        # Otherwise use explicit scale on original height.
        scale = self.cameras("rear").scale or 1
        return int(self.cameras("rear").height_fixed * scale)


class Cross(MovieLayout):
    """Cross Movie Layout

               [   FRONT_CAMERA    ]
    [LEFT-PILLAR_CAMERA][RIGHT-PILLAR_CAMERA]
    [   LEFT_CAMERA    ][   RIGHT_CAMERA    ]
               [   REAR_CAMERA    ]
    """

    def __init__(self) -> None:
        super().__init__()
        self.scale = 1 / 2

    @property
    def _pillar_row_width(self) -> int:
        return self.cameras("left_pillar").width + self.cameras("right_pillar").width

    @property
    def _repeater_row_width(self) -> int:
        return self.cameras("left").width + self.cameras("right").width

    @property
    def _row_width(self) -> int:
        return max(
            self.cameras("front").width,
            self._pillar_row_width,
            self._repeater_row_width,
            self.cameras("rear").width,
        )

    @property
    def _pillar_row_xpos(self) -> int:
        return int(self._row_width / 2) - int(self._pillar_row_width / 2)

    @property
    def _repeater_row_xpos(self) -> int:
        return int(self._row_width / 2) - int(self._repeater_row_width / 2)

    @property
    def _pillar_row_height(self) -> int:
        return max(
            self.cameras("left_pillar").height, self.cameras("right_pillar").height
        )

    @property
    def _repeater_row_height(self) -> int:
        return max(self.cameras("left").height, self.cameras("right").height)

    @property
    def _pillar_row_ypos(self) -> int:
        return self.cameras("front").height

    @property
    def _repeater_row_ypos(self) -> int:
        return self.cameras("front").height + self._pillar_row_height

    def front_xpos(self) -> int:
        return int(self._row_width / 2) - int(self.cameras("front").width / 2)

    def left_pillar_xpos(self) -> int:
        return self._pillar_row_xpos

    def right_pillar_xpos(self) -> int:
        return self._pillar_row_xpos + self.cameras("left_pillar").width

    def left_xpos(self) -> int:
        return self._repeater_row_xpos

    def right_xpos(self) -> int:
        return self._repeater_row_xpos + self.cameras("left").width

    def rear_xpos(self) -> int:
        return int(self._row_width / 2) - int(self.cameras("rear").width / 2)

    def left_pillar_ypos(self) -> int:
        return self._pillar_row_ypos + int(
            (self._pillar_row_height - self.cameras("left_pillar").height) / 2
        )

    def right_pillar_ypos(self) -> int:
        return self._pillar_row_ypos + int(
            (self._pillar_row_height - self.cameras("right_pillar").height) / 2
        )

    def left_ypos(self) -> int:
        return self._repeater_row_ypos + int(
            (self._repeater_row_height - self.cameras("left").height) / 2
        )

    def right_ypos(self) -> int:
        return self._repeater_row_ypos + int(
            (self._repeater_row_height - self.cameras("right").height) / 2
        )

    def rear_ypos(self) -> int:
        return (
            self.cameras("front").height
            + self._pillar_row_height
            + self._repeater_row_height
        )


class Diamond(MovieLayout):
    """Diamond Movie Layout

                        [            ]
    [LEFT-PILLAR_CAMERA][FRONT_CAMERA][RIGHT-PILLAR_CAMERA]
    [   LEFT_CAMERA    ][REAR_CAMERA ][   RIGHT_CAMERA    ]
                        [            ]
    """

    def __init__(self) -> None:
        super().__init__()
        self._font.valign = "MIDDLE"
        self.scale = 1 / 2
        self.cameras("front").scale = 1
        self.cameras("rear").scale = 1

    @property
    def _left_column_width(self) -> int:
        return max(self.cameras("left_pillar").width, self.cameras("left").width)

    @property
    def _front_rear_column_width(self) -> int:
        return max(self.cameras("front").width, self.cameras("rear").width)

    @property
    def _right_column_width(self) -> int:
        return max(self.cameras("right_pillar").width, self.cameras("right").width)

    @property
    def _pillar_row_height(self) -> int:
        return max(
            self.cameras("left_pillar").height, self.cameras("right_pillar").height
        )

    @property
    def _repeater_row_height(self) -> int:
        return max(self.cameras("left").height, self.cameras("right").height)

    @property
    def _pillar_repeater_row_height(self) -> int:
        return self._pillar_row_height + self._repeater_row_height

    @property
    def _left_column_height(self) -> int:
        return self.cameras("left_pillar").height + self.cameras("left").height

    @property
    def _front_rear_height(self) -> int:
        return self.cameras("front").height + self.cameras("rear").height

    @property
    def _right_column_height(self) -> int:
        return self.cameras("right_pillar").height + self.cameras("right").height

    def front_xpos(self) -> int:
        return self._left_column_width + int(
            (self._front_rear_column_width - self.cameras("front").width) / 2
        )

    def left_pillar_xpos(self) -> int:
        return self._left_column_width - self.cameras("left_pillar").width

    def left_xpos(self) -> int:
        return self._left_column_width - self.cameras("left").width

    def right_pillar_xpos(self) -> int:
        return self._left_column_width + self._front_rear_column_width

    def right_xpos(self) -> int:
        return self._left_column_width + self._front_rear_column_width

    def rear_xpos(self) -> int:
        return self._left_column_width + int(
            (self._front_rear_column_width - self.cameras("rear").width) / 2
        )

    def front_ypos(self) -> int:
        return int(
            max(
                0,
                (
                    max(self._left_column_height, self._right_column_height)
                    - self._front_rear_height
                )
                / 2,
            )
        )

    def left_pillar_ypos(self) -> int:
        return int(max(0, (self._front_rear_height - self._left_column_height) / 2))

    def left_ypos(self) -> int:
        return int(
            (
                max(0, (self._front_rear_height - self._left_column_height) / 2)
                + self.cameras("left_pillar").height
            )
        )

    def right_pillar_ypos(self) -> int:
        return int(max(0, (self._front_rear_height - self._right_column_height) / 2))

    def right_ypos(self) -> int:
        return int(
            max(0, (self._front_rear_height - self._right_column_height) / 2)
            + self.cameras("right_pillar").height
        )

    def rear_ypos(self) -> int:
        return int(
            max(
                0,
                (
                    max(self._left_column_height, self._right_column_height)
                    - self._front_rear_height
                )
                / 2,
            )
            + self.cameras("front").height
        )


class Horizontal(MovieLayout):
    """Horizontal Movie Layout

    [LEFT_CAMERA][LEFT_PILLAR][FRONT_CAMERA][REAR_CAMERA][RIGHT_PILLAR][RIGHT_CAMERA]
    """

    def __init__(self) -> None:
        """Initialize Horizontal Layout."""
        super().__init__()
        self.scale = 1 / 2

    @property
    def _row_height(self) -> int:
        return max(
            self.cameras("left").height,
            self.cameras("left_pillar").height,
            self.cameras("front").height,
            self.cameras("rear").height,
            self.cameras("right_pillar").height,
            self.cameras("right").height,
        )

    def left_ypos(self) -> int:
        return int((self._row_height - self.cameras("left").height) / 2)

    def left_pillar_xpos(self) -> int:
        return self.cameras("left").width

    def left_pillar_ypos(self) -> int:
        return int((self._row_height - self.cameras("left_pillar").height) / 2)

    def front_xpos(self) -> int:
        return self.cameras("left").width + self.cameras("left_pillar").width

    def front_ypos(self) -> int:
        return int((self._row_height - self.cameras("front").height) / 2)

    def rear_xpos(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("left_pillar").width
            + self.cameras("front").width
        )

    def rear_ypos(self) -> int:
        return int((self._row_height - self.cameras("rear").height) / 2)

    def right_pillar_xpos(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("left_pillar").width
            + self.cameras("front").width
            + self.cameras("rear").width
        )

    def right_pillar_ypos(self) -> int:
        return int((self._row_height - self.cameras("right_pillar").height) / 2)

    def right_xpos(self) -> int:
        return (
            self.cameras("left").width
            + self.cameras("left_pillar").width
            + self.cameras("front").width
            + self.cameras("rear").width
            + self.cameras("right_pillar").width
        )

    def right_ypos(self) -> int:
        return int((self._row_height - self.cameras("right").height) / 2)


class MyArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, arg_line) -> list[str]:
        # Remove comments.
        return shlex_split(arg_line, comments=True)

    def args_to_dict(self, arguments, default) -> list:
        argument_list: list = []

        if arguments is None:
            return argument_list

        for argument in arguments:
            argument_dict = {}
            for argument_value in argument:
                if "=" in argument_value:
                    key = argument_value.split("=")[0].lower()
                    value = (
                        argument_value.split("=")[1].strip()
                        if argument_value.split("=")[1].strip() != ""
                        else None
                    )
                else:
                    key = default
                    value = argument_value
                argument_dict.update({key: value})

            argument_list.append(argument_dict)
        return argument_list


class SmartFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Formatter for argument help."""

    def _split_lines(self, text: str, width: int) -> list[str]:
        """Provide raw output allowing for prettier help output"""
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return super()._split_lines(text, width)


def get_class_properties(
    instance: object, max_depth: int = 3, _depth: int = 0, _seen: set | None = None
):
    if _seen is None:
        _seen = set()
    if id(instance) in _seen or _depth >= max_depth:
        return "<circular or max depth reached>"
    _seen.add(id(instance))

    properties: dict[str, Any] = {}
    for attr_name in dir(instance):
        if attr_name.startswith("_"):
            continue  # Skip private/internal
        try:
            attr_value = getattr(instance, attr_name)
        except AttributeError as e:
            properties[attr_name] = f"<error reading value> ({e})"
        else:
            if isroutine(attr_value):
                continue  # Skip methods
            if isinstance(
                attr_value, (int, float, str, bool, list, dict, tuple, type(None))
            ):
                properties[attr_name] = attr_value
            elif hasattr(attr_value, "__dict__") or not isclass(attr_value):
                # Likely a custom object — dig deeper
                properties[attr_name] = get_class_properties(
                    attr_value, max_depth=max_depth, _depth=_depth + 1, _seen=_seen
                )
            else:
                properties[attr_name] = repr(attr_value)
    return properties


def search_dict(
    key: str, search_list: List[dict], match_value: object = None
) -> Optional[dict]:
    """
    Returns the 1st element in a list containing dictionaries
    where the value of key provided matches the value provided.

    :param match_value: value to match upon (search for)
    :type match_value: object
    :param key: dictionary key to use for the match
    :type key: str
    :param search_list: List containing dictionary objects in which to search
    :type search_list: List[dict]
    :return: Dictionary object that matches
    :rtype: dict
    """
    if key == "" or len(search_list) == 0:
        return None

    if match_value is None:
        return next(
            (element for element in search_list if element.get(key) is None), None
        )

    return next(
        (element for element in search_list if element.get(key) == match_value), None
    )


def escape_drawtext_literals(text: str) -> str:
    """Escape literal colons for drawtext while preserving %{...} expansions."""

    def is_escaped(pos: int) -> bool:
        """Return True when the character at pos is already escaped."""
        backslash_count = 0
        idx = pos - 1
        while idx >= 0 and text[idx] == "\\":
            backslash_count += 1
            idx -= 1
        return backslash_count % 2 == 1

    escaped: list[str] = []
    inside_expansion = False
    idx = 0
    text_length = len(text)

    while idx < text_length:
        char = text[idx]
        next_char = text[idx + 1] if idx + 1 < text_length else ""

        if (
            not inside_expansion
            and char == "%"
            and next_char == "{"
            and not is_escaped(idx)
        ):
            inside_expansion = True
            escaped.append("%{")
            idx += 2
            continue

        if inside_expansion and char == "}" and not is_escaped(idx):
            inside_expansion = False
            escaped.append("}")
            idx += 1
            continue

        if char == ":" and not inside_expansion and not is_escaped(idx):
            escaped.append(r"\:")
        else:
            escaped.append(char)

        idx += 1

    return "".join(escaped)


def get_current_timestamp() -> str:
    """Returns the current timestamp"""
    if DISPLAY_TS:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S - ")
    return ""


def check_latest_release(include_beta: bool = False) -> Optional[dict[str, str]]:
    """Checks GitHub for latest release"""

    url: str = f"{GITHUB['URL']}/repos/{GITHUB['owner']}/{GITHUB['repo']}/releases"

    if not include_beta:
        url = url + "/latest"
    try:
        releases = requests.get(url, timeout=30)
    except requests.exceptions.RequestException as exc:
        print(f"{get_current_timestamp()}Unable to check for latest release: {exc}")
        return None

    release_data = releases.json()
    # If we include betas then we would have received a list, thus get 1st
    # element as that is the latest release.
    if include_beta:
        if not release_data or len(release_data) == 0:
            print(f"{get_current_timestamp()}No releases found")
            return None
        release_data = release_data[0]

    return release_data


def get_tesladashcam_folder() -> tuple[Optional[str], Optional[str]]:
    """Check if there is a drive mounted with the Tesla DashCam folder."""
    for partition in disk_partitions(all=False):
        if "cdrom" in partition.opts or partition.fstype == "":
            continue

        teslacamfolder: str = os.path.join(partition.mountpoint, "TeslaCam")
        if os.path.isdir(teslacamfolder):
            _LOGGER.debug(
                "Folder TeslaCam found on partition %s.", partition.mountpoint
            )
            return teslacamfolder, partition.mountpoint
        _LOGGER.debug("No TeslaCam folder on partition %s.", partition.mountpoint)
    return None, None


def get_movie_files(
    source_folder: list[str], video_settings: dict[str, Any]
) -> dict[str, Event]:
    """Find all the clip files within folder (and subfolder if requested)"""

    # Making as a set to ensure uniqueness.
    folder_list: set[str] = set()
    # Determine all the folders to scan for files. Using a SET ensuring uniqueness for
    # the folders.
    _LOGGER.debug("Determining all the folders to scan for video files")
    for source_pathname in source_folder:
        _LOGGER.debug("Processing provided source path %s.", source_pathname)
        for pathname in iglob(os.path.expanduser(os.path.expandvars(source_pathname))):
            _LOGGER.debug("Processing %s.", pathname)
            if (
                os.path.isdir(pathname)
                or os.path.ismount(pathname)
                and not video_settings["exclude_subdirs"]
            ):
                _LOGGER.debug("Retrieving all subfolders for %s.", pathname)
                for folder, _, _ in os.walk(pathname, followlinks=True):
                    folder_list.add(folder)
            else:
                folder_list.add(pathname)

    events_list: dict[str, Event] = {}
    # Go through each folder, get the movie files within it and add to movie list.
    # Sorting folder list 1st.
    print(f"{get_current_timestamp()}Scanning {len(folder_list)} folder(s)")
    folders_scanned: int = 0
    for event_folder in sorted(folder_list):
        if folders_scanned % 10 == 0 and folders_scanned != 0:
            print(f"Scanned {folders_scanned}/{len(folder_list)}.")
        folders_scanned = folders_scanned + 1

        if os.path.isdir(event_folder):
            _LOGGER.debug("Retrieving all video files in folder %s.", event_folder)
            event_info: Event | None = None

            # Collect video files within folder and process.
            for clip_filename in glob(os.path.join(event_folder, "*.mp4")):
                # Get the timestamp of the filename.
                _, clip_filename_only = os.path.split(clip_filename)
                clip_timestamp = clip_filename_only.rsplit("-", 1)[0]

                # We get the clip starting time from the filename and provided
                # that as initial timestamp.
                # Tesla stores these timestamps in local timezone.
                if len(clip_timestamp) == 16:
                    # This is for before version 2019.16
                    try:
                        clip_starting_timestamp = datetime.strptime(
                            clip_timestamp, "%Y-%m-%d_%H-%M"
                        )
                    except ValueError:
                        _LOGGER.debug(
                            "Invalid timestamp format in filename %s. Expected format "
                            "is YYYY-MM-DD_HH-MM.",
                            clip_filename_only,
                        )
                        continue
                    # Treat filename timestamps as local time, then normalize to UTC
                    clip_starting_timestamp = clip_starting_timestamp.replace(
                        tzinfo=get_localzone()
                    ).astimezone(timezone.utc)
                else:
                    # This is for version 2019.16 and later
                    try:
                        clip_starting_timestamp = datetime.strptime(
                            clip_timestamp, "%Y-%m-%d_%H-%M-%S"
                        )
                    except ValueError:
                        _LOGGER.debug(
                            "Invalid timestamp format in filename %s. Expected format "
                            "is YYYY-MM-DD_HH-MM.",
                            clip_filename_only,
                        )
                        continue
                    # Treat filename timestamps as local time, then normalize to UTC
                    clip_starting_timestamp = clip_starting_timestamp.replace(
                        tzinfo=get_localzone()
                    ).astimezone(timezone.utc)

                # Check if we already processed this timestamp.
                if (
                    event_info is not None
                    and event_info.clip(clip_starting_timestamp) is not None
                ):
                    # Already processed this clip, moving on.
                    continue

                front_filename = f"{str(clip_timestamp)}-front.mp4"
                front_path = os.path.join(event_folder, front_filename)

                left_filename = f"{str(clip_timestamp)}-left_repeater.mp4"
                left_path = os.path.join(event_folder, left_filename)

                right_filename = f"{str(clip_timestamp)}-right_repeater.mp4"
                right_path = os.path.join(event_folder, right_filename)

                rear_filename = f"{str(clip_timestamp)}-back.mp4"
                rear_path = os.path.join(event_folder, rear_filename)

                left_pillar_filename = f"{str(clip_timestamp)}-left_pillar.mp4"
                left_pillar_path = os.path.join(event_folder, left_pillar_filename)

                right_pillar_filename = f"{str(clip_timestamp)}-right_pillar.mp4"
                right_pillar_path = os.path.join(event_folder, right_pillar_filename)

                # Get meta data for each camera for this timestamp to determine
                # creation time and duration.
                metadata = get_metadata(
                    video_settings["ffmpeg_exec"],
                    [
                        front_path,
                        left_path,
                        right_path,
                        rear_path,
                        left_pillar_path,
                        right_pillar_path,
                    ],
                )

                # Move on to next one if nothing received.
                if not metadata:
                    _LOGGER.debug(
                        "No camera files in folder %s with timestamp %s found.",
                        event_folder,
                        clip_timestamp,
                    )
                    continue

                clip_info: Clip | None = None
                camera: str = ""
                # Store filename, duration, timestamp, and if has to be included for
                # each camera
                for item in metadata:
                    _, filename = os.path.split(item.filename)
                    if filename == front_filename:
                        if video_settings["video_layout"].swap_front_rear:
                            camera = "rear"
                        else:
                            camera = "front"
                    elif filename == left_filename:
                        if video_settings["video_layout"].swap_left_right:
                            camera = "right"
                        else:
                            camera = "left"
                    elif filename == right_filename:
                        if video_settings["video_layout"].swap_left_right:
                            camera = "left"
                        else:
                            camera = "right"
                    elif filename == rear_filename:
                        if video_settings["video_layout"].swap_front_rear:
                            camera = "front"
                        else:
                            camera = "rear"
                    elif filename == left_pillar_filename:
                        if video_settings["video_layout"].swap_pillar:
                            camera = "right_pillar"
                        else:
                            camera = "left_pillar"
                    elif filename == right_pillar_filename:
                        if video_settings["video_layout"].swap_pillar:
                            camera = "left_pillar"
                        else:
                            camera = "right_pillar"
                    else:
                        continue

                    if clip_info is None:
                        clip_info = Clip(timestmp=clip_starting_timestamp)

                    clip_camera_info = Camera_Clip(
                        filename=filename,
                        duration=item.duration,
                        timestmp=(
                            item.timestamp
                            if item.timestamp is not None
                            else clip_starting_timestamp
                        ),
                        include=(
                            item.include
                            if video_settings["video_layout"].cameras(camera).include
                            else False
                        ),
                        video_metadata=item,
                    )

                    # Store the camera information in the clip.
                    clip_info.set_camera(camera, clip_camera_info)
                    if event_info is None:
                        event_info = Event(folder=event_folder)
                    event_info.add_camera_clip(camera)

                # Not storing anything if no cameras included for this clip.
                if clip_info is None or event_info is None:
                    _LOGGER.debug(
                        "No valid camera files in folder %s with timestamp %s",
                        event_folder,
                        clip_timestamp,
                    )
                    continue

                # Store the clip information in the event
                event_info.set_clip(clip_starting_timestamp, clip_info)

            # Got all the clip information for this event (folder)
            # If no clips found then skip this folder and continue on.
            if event_info is None:
                _LOGGER.debug("No clips found in folder %s", event_folder)
                continue

            _LOGGER.debug("Found %d clips in folder %s", event_info.count, event_folder)
            # We have clips for this event, get the event meta data.
            event_metadata_file = os.path.join(event_folder, "event.json")
            if os.path.isfile(event_metadata_file):
                _LOGGER.debug("Folder %s has an event file.", event_folder)
                try:
                    with open(event_metadata_file, encoding="utf-8") as f:
                        event_file_data: dict[str, Any] = json.load(f)
                except json.JSONDecodeError as e:
                    _LOGGER.warning(
                        "Event JSON found in %s failed to parse with JSON error: %s",
                        event_metadata_file,
                        str(e),
                    )
                except (OSError, IOError) as exc:
                    _LOGGER.warning(
                        "Error opening or reading %s: %s",
                        event_metadata_file,
                        exc,
                    )
                else:
                    event_timestamp: str | None = None
                    if (
                        event_timestamp := event_file_data.get("timestamp")
                    ) is not None:
                        # Convert string to timestamp.
                        try:
                            event_timestamp_dt = datetime.strptime(
                                event_timestamp, "%Y-%m-%dT%H:%M:%S"
                            )
                        except ValueError:
                            _LOGGER.warning(
                                "Event timestamp (%s) found in %s could not be parsed "
                                "as a timestamp",
                                event_timestamp,
                                event_metadata_file,
                            )
                            event_timestamp = None
                        else:
                            # Assign local tz to JSON timestamp, then convert to UTC
                            event_timestamp_dt = event_timestamp_dt.replace(
                                tzinfo=get_localzone()
                            ).astimezone(timezone.utc)
                    event_info.event_metadata.timestamp = event_timestamp_dt
                    event_info.event_metadata.city = event_file_data.get("city", "n/a")
                    event_info.event_metadata.street = event_file_data.get(
                        "street", "n/a"
                    )

                    # Try to get the event reason.
                    # If it is not in the EVENT_REASON dict then try to match it
                    # If it is not in the EVENT_REASON dict and no match then
                    # leave it as None
                    if (event_file_reason := event_file_data.get("reason")) is not None:
                        if (
                            event_reason := EVENT_REASON.get(event_file_reason)
                        ) is None:
                            for event_reason in EVENT_REASON:
                                if match(event_reason, event_file_reason):
                                    break
                        event_info.event_metadata.reason = event_reason or "n/a"

                    if (event_latitude := event_file_data.get("est_lat")) is not None:
                        try:
                            event_latitude = float(event_latitude)
                        except ValueError:
                            pass
                        event_info.event_metadata.latitude = event_latitude

                    if (event_longitude := event_file_data.get("est_lon")) is not None:
                        try:
                            event_longitude = float(event_longitude)
                        except ValueError:
                            pass
                        event_info.event_metadata.longitude = event_longitude

        else:
            _LOGGER.debug("Adding video file %s.", event_folder)
            # Get the metadata for this video files.
            metadata = get_metadata(video_settings["ffmpeg_exec"], [event_folder])
            if not metadata:
                _LOGGER.warning(
                    "Failed to get metadata for file %s, skipping.", event_folder
                )
                continue

            # Store video as a camera clip.
            clip_timestamp_dt = (
                metadata[0].timestamp
                if metadata[0].timestamp is not None
                # Use local timezone to avoid mixing naive/aware timestamps when
                # user-provided start/end timestamps are tz-aware.
                else datetime.fromtimestamp(
                    os.path.getmtime(event_folder), tz=get_localzone()
                )
            )
            # Normalize to UTC for internal comparisons
            clip_timestamp_dt = clip_timestamp_dt.astimezone(timezone.utc)

            clip_camera_info = Camera_Clip(
                filename=event_folder,
                duration=metadata[0].duration,
                timestmp=clip_timestamp_dt
                if clip_timestamp_dt is not None
                else datetime.now(timezone.utc),
                include=True,
                video_metadata=metadata[0],
            )
            # Add it as a clip
            clip_info = Clip(timestmp=clip_camera_info.timestamp)
            clip_info.set_camera("FULL", clip_camera_info)
            # And now store as an event.
            event_info = Event(
                folder=event_folder,
                isfile=True,
                filename=event_folder,
                video_metadata=metadata[0],
            )
            # Ensure direct-file events have a clip entry for processing/trimming
            event_info.set_clip(clip_camera_info.timestamp, clip_info)
            event_info.add_camera_clip("FULL")

        # Now add the event folder to our events list.
        events_list.update({event_folder: event_info})

    _LOGGER.debug("%d folders contain clips.", len(events_list))
    return events_list


def get_metadata(ffmpeg: str, filenames: list[str]) -> list[Video_Metadata]:  #
    """Retrieve the meta data for the clip (i.e. timestamp, duration)"""
    # Get meta data for each video to determine creation time and duration.
    ffmpeg_command = [ffmpeg]

    metadata: list[Video_Metadata] = []
    for camera_file in filenames:
        if os.path.isfile(camera_file):
            ffmpeg_command.append("-i")
            ffmpeg_command.append(camera_file)
            metadata.append(Video_Metadata(filename=camera_file))
        else:
            _LOGGER.debug("File %s does not exist, skipping.", camera_file)

    # Don't run ffmpeg if nothing to check for.
    if not metadata:
        return metadata

    ffmpeg_command.append("-hide_banner")

    try:
        command_result = run(
            ffmpeg_command, capture_output=True, text=True, check=False
        )
    except OSError as e:
        _LOGGER.error(
            "Error occurred while running ffmpeg: %s. Is ffmpeg installed and in PATH?",
            e,
        )
        return metadata

    # If we got here then we have the metadata, now parse it.

    # Create an iterator for the metadata list.
    # This is to ensure that we can keep track of which metadata item we're processing.
    metadata_iterator: Iterator[Video_Metadata] = iter(metadata)

    metadata_item: Optional[Video_Metadata] = None
    chapter_info: Optional[Chapter] = None
    for line in command_result.stderr.splitlines():
        if search("^Input #", line) is not None:
            # If filename was not yet appended then it means it is a corrupt file, in
            # that case just add to list for
            # but identify not to include for processing
            metadata_item = next(metadata_iterator)
            chapter_info = None
            continue

        if metadata_item is None:
            continue

        # Are we processing chapters?
        if chapter_info:
            if search(r"^\s*Chapter #\d+:", line) is not None:
                if (
                    chapter_match := search(r"start ([\d\.]+), end ([\d\.]+)", line)
                ) is not None:
                    chapter_info.start = float(chapter_match.group(1))
                    chapter_info.end = float(chapter_match.group(2))
                continue

            if search(r"^\s*Metadata:", line) is not None:
                # Metadata line, we can skip it.
                continue

            # Title of the chapter
            if (title_match := search(r"^\s*title\s*:\s*(.+)", line)) is not None:
                chapter_info.title = title_match.group(1).strip()

                # And this is the last item so we can append it.
                metadata_item.add_chapter(chapter_info)
                chapter_info = None
                continue

        # Start of chapters in the video metadata
        if search(r"^\s*Chapters:", line) is not None:
            chapter_info = Chapter()
            continue

        # If we're here then we're done processing chapters.
        chapter_info = None

        # Creation time of the video
        if (
            match_videotime := search(r"^\s*creation_time\s*:\s*(.+)", line)
        ) is not None:
            parsed_time = datetime.strptime(
                match_videotime.group(1).strip(), "%Y-%m-%dT%H:%M:%S.%f%z"
            ).astimezone(timezone.utc)
            _LOGGER.debug(
                f"Parsed clip timestamp: {parsed_time}, tzinfo: {parsed_time.tzinfo}"
            )
            metadata_item.timestamp = parsed_time
            continue

        # Title of the video
        if (match_title := search(r"^\s*title\s*:\s*(.+)", line)) is not None:
            metadata_item.title = match_title.group(1).strip()
            continue

        # Duration of the video
        if search("^ *Duration: ", line) is not None:
            line_split = line.split(",")
            line_split = line_split[0].split(":", 1)
            duration_list = line_split[1].split(":")
            try:
                hours = int(duration_list[0])
                minutes = int(duration_list[1])
                seconds = float(duration_list[2])
                metadata_item.duration = hours * 3600 + minutes * 60 + seconds
            except ValueError:
                _LOGGER.warning(
                    "Duration in file %s contains invalid data and "
                    "will be excluded: %s",
                    metadata_item.filename,
                    line_split,
                )
            else:
                # File will only be processed if duration is greater then 0
                metadata_item.include = metadata_item.duration > 0

            if metadata_item.timestamp is None:
                _LOGGER.warning(
                    "Did not find a creation_time in metadata for file %s",
                    metadata_item.filename,
                )
            continue

        # Get the stream info which contains codec, resolution, and fps.
        # First check if this is a stream line.
        if (
            search(
                r"^\s*Stream\s+#\d+:0",
                line,
            )
        ) is not None:
            # 1. Video codec
            if m := search(r"Video:\s*(\w+)", line):
                metadata_item.video_codec = m.group(1)

            # 2. Width and height
            if m := search(r"Video:.*,\s*(\d+)x(\d+)\s*[,|\[]", line):
                metadata_item.width, metadata_item.height = (
                    int(m.group(1)),
                    int(m.group(2)),
                )

            # 3. DAR (Display Aspect Ratio)
            if m := search(r"DAR\s*([0-9:]+)", line):
                metadata_item.dar = m.group(1)

            # 4. FPS
            if m := search(r"([\d.]+)\s*fps", line):
                metadata_item.fps = float(m.group(1) or 24.0)

    return metadata


def create_intermediate_movie(
    event_info: Event,
    clip_info: Clip,
    folder_timestamps: tuple[datetime, datetime],
    video_settings: dict[str, Any],
    clip_number: int,
) -> bool:
    """Create intermediate movie files. This is the merging of the camera

    video files into 1 video file."""
    # We first stack (combine the different camera video files into 1
    # and then we concatenate.
    clip_filenames: dict[str, str] = {}
    video_layout: MovieLayout = video_settings["video_layout"]

    # Loop through the camera clips and get the filenames.
    for camera_name, camera_info in clip_info.cameras:
        camera_filename = os.path.join(event_info.folder, camera_info.filename)
        clip_filenames.update({camera_name: camera_filename})

        # The ratio can be different, so we'll be storing the largest one we can find.
        # For example, on Model 3 Highlander the front camera is 2896x1876 instead of
        # 1280x960 hence ratio is about 4/2.65 instead of 4/3.
        camera_element: Camera = video_layout.cameras(camera_name)
        if (
            camera_element.clip_ratio is not None
            and camera_element.clip_ratio < camera_info.ratio
        ):
            camera_element.clip_ratio = camera_info.ratio

    if len(clip_filenames) == 0:
        _LOGGER.debug(
            "No valid front, left, right, left-pillar, right-pillar, and rear camera "
            "clip exist for %s",
            clip_info.timestamp.astimezone(get_localzone()).strftime(
                "%Y-%m-%dT%H-%M-%S"
            ),
        )
        return True

    # Determine if this clip is to be included based on potential start and end
    # timestamp/offsets that were provided.
    # Clip starting time is between the start&end times we're looking for
    # or Clip end time is between the start&end time we're looking for.
    # or Starting time is between start&end clip time
    # or End time is between start&end clip time
    starting_timestamp: datetime = clip_info.start_timestamp
    ending_timestamp: datetime = clip_info.end_timestamp
    if not (
        folder_timestamps[0] <= starting_timestamp <= folder_timestamps[1]
        or folder_timestamps[0] <= ending_timestamp <= folder_timestamps[1]
        or starting_timestamp <= folder_timestamps[0] <= ending_timestamp
        or starting_timestamp <= folder_timestamps[1] <= ending_timestamp
    ):
        # This clip is not in-between the timestamps we want, skip it.
        _LOGGER.debug(
            "Clip timestamp from %s to %s not between %s and %s",
            starting_timestamp,
            ending_timestamp,
            folder_timestamps[0],
            folder_timestamps[1],
        )
        return True

    # Determine if we need to do an offset of the starting timestamp
    ffmpeg_offset_command: list[str] = []
    clip_duration: float = clip_info.duration

    # This clip falls in between the start and end timestamps to include.
    # Set offsets if required
    if starting_timestamp < folder_timestamps[0]:
        # Starting timestamp is withing this clip.
        starting_offset = (folder_timestamps[0] - starting_timestamp).total_seconds()
        starting_timestamp = folder_timestamps[0]
        clip_duration = (ending_timestamp - starting_timestamp).total_seconds()
        ffmpeg_offset_command = ["-ss", str(starting_offset)]
        _LOGGER.debug(
            "Clip start offset by %d seconds due to start timestamp requested.",
            starting_offset,
        )

    # Adjust duration if end of clip's timestamp is after ending timestamp we need.
    if ending_timestamp > folder_timestamps[1]:
        ending_timestamp = folder_timestamps[1]
        prev_clip_duration = clip_duration
        clip_duration = (ending_timestamp - starting_timestamp).total_seconds()
        ffmpeg_offset_command += ["-t", str(clip_duration)]
        _LOGGER.debug(
            "Clip duration reduced from %d to %d seconds due to end timestamp "
            "requested.",
            prev_clip_duration,
            clip_duration,
        )

    # Make sure our duration does not end up with 0, if it does then do not continue.
    if int(clip_duration) <= 0:
        _LOGGER.debug(
            "Clip duration is %d, not processing as no valid video.",
            clip_duration,
        )
        return True

    ffmpeg_camera_commands: list[str] = []
    ffmpeg_camera_filters: list[str] = []
    ffmpeg_camera_positions: list[str] = []

    # Inform the layout of the current event as this will be used to determine if
    # clips should be included or not.
    video_layout.event = event_info

    black_base = "color=duration={duration}:"
    black_size = (
        f"s={{width}}x{{height}}:c={video_layout.background_color}, "
        f"fps={str(video_settings['fps'])} "
    )
    ffmpeg_black_video = ";" + black_base + black_size

    # Always starting from base.
    input_clip: str = "base"
    camera: str = ""
    input_counter: int = 0
    for camera in video_layout.clip_order:
        # Is this camera to be included?
        camera_element = video_layout.cameras(camera)
        if camera_element.include:
            # We have a camera clip for this camera, use it.
            if (clip_filename := clip_filenames.get(camera)) is None:
                # We do not have a camera clip for this camera, use background instead.
                ffmpeg_camera_filters.append(
                    ffmpeg_black_video.format(
                        duration=clip_duration,
                        speed=video_settings["movie_speed"],
                        width=camera_element.width,
                        height=camera_element.height,
                    )
                    + f"[{camera}]"
                )
                ffmpeg_camera_positions.append(
                    f";[{input_clip}][{camera}]"
                    + " overlay=eof_action=pass:repeatlast=0"
                    + f":x={str(camera_element.xpos)}"
                    + f":y={str(camera_element.ypos)}, setsar=1"
                    + f" [{camera}1]"
                )
                input_clip = f"{camera}1"
            else:
                # Got a valid clip for this camera and to be included
                ffmpeg_camera_commands.extend(
                    ffmpeg_offset_command + ["-i", clip_filename]
                )
                ffmpeg_camera_filters.append(
                    ";["
                    + str(input_counter)
                    + ":v] "
                    + "setpts=PTS-STARTPTS, setsar=1, "
                    + f"scale={camera_element.scale_width}x"
                    + f"{camera_element.scale_height}"
                    + f"{camera_element.mirror_text}"
                    + f"{camera_element.options}"
                    + f" [{camera}]"
                )
                input_counter += 1

                ffmpeg_camera_positions.append(
                    f";[{input_clip}][{camera}]"
                    + " overlay=eof_action=pass:repeatlast=0"
                    + f":x={str(camera_element.xpos)}"
                    + f":y={str(camera_element.ypos)}"
                    + f" [{camera}1]"
                )
                input_clip = f"{camera}1"

    local_timestamp: datetime = clip_info.timestamp.astimezone(get_localzone())

    # Check if target video file exist if skip existing.
    file_already_exist: bool = False
    if video_settings["skip_existing"]:
        temp_movie_name: str = (
            os.path.join(
                video_settings["target_folder"],
                local_timestamp.strftime("%Y-%m-%dT%H-%M-%S"),
            )
            + ".mp4"
        )
        if os.path.isfile(temp_movie_name):
            file_already_exist = True
        elif (
            not video_settings["keep_intermediate"]
            and video_settings["temp_dir"] is not None
        ):
            temp_movie_name = (
                os.path.join(
                    video_settings["temp_dir"],
                    local_timestamp.strftime("%Y-%m-%dT%H-%M-%S"),
                )
                + ".mp4"
            )
            if os.path.isfile(temp_movie_name):
                file_already_exist = True

        if file_already_exist:
            print(
                f"{get_current_timestamp()}\t\tSkipping clip {clip_number + 1}/"
                f"{event_info.count} from {local_timestamp.strftime('%x %X')} and "
                f"{int(clip_duration)} seconds as it already exist."
            )
            clip_info.filename = temp_movie_name
            clip_info.start_timestamp = starting_timestamp
            clip_info.end_timestamp = ending_timestamp
            # Get actual duration of our new video, required for chapters when
            # concatenating.
            metadata = get_metadata(video_settings["ffmpeg_exec"], [temp_movie_name])
            if metadata:
                clip_info.duration = metadata[0].duration
                clip_info.video_metadata = metadata[0]

            return True
    else:
        target_folder: str = (
            video_settings["temp_dir"]
            if not video_settings["keep_intermediate"]
            and video_settings["temp_dir"] is not None
            else video_settings["target_folder"]
        )
        temp_movie_name = os.path.join(
            target_folder, local_timestamp.strftime("%Y-%m-%dT%H-%M-%S") + ".mp4"
        )

    print(
        f"{get_current_timestamp()}\t\tProcessing clip {clip_number + 1}/"
        f"{event_info.count} from {local_timestamp.strftime('%x %X')} and "
        f"{int(clip_duration)} seconds long."
    )

    starting_epoch_timestamp: int = int(starting_timestamp.timestamp())

    ffmpeg_text: str = video_settings["ffmpeg_text_overlay"].format(
        input_clip=input_clip
    )
    user_formatted_text: str = video_settings["text_overlay_format"]
    user_timestamp_format = video_settings["timestamp_format"]
    ffmpeg_user_timestamp_format = user_timestamp_format.replace(":", r"\\\:")

    # Replace variables in user provided text overlay
    replacement_strings: dict[str, str | float] = {
        "start_timestamp": starting_timestamp.astimezone(get_localzone()).strftime(
            user_timestamp_format
        ),
        "end_timestamp": ending_timestamp.astimezone(get_localzone()).strftime(
            user_timestamp_format
        ),
        "local_timestamp_rolling": (
            f"%{{pts\\:localtime\\:{starting_epoch_timestamp}\\:"
            f"{ffmpeg_user_timestamp_format}}}"
        ),
        "event_timestamp_countdown": "n/a",
        "event_timestamp_countdown_rolling": "n/a",
        "event_timestamp": "n/a",
        "event_city": "n/a",
        "event_street": "n/a",
        "event_reason": "n/a",
        "event_latitude": 0.0,
        "event_longitude": 0.0,
    }

    if event_info.event_metadata.timestamp:
        event_epoch_timestamp = int(event_info.timestamp.timestamp())
        replacement_strings["event_timestamp"] = (
            event_info.event_metadata.timestamp.astimezone(get_localzone()).strftime(
                user_timestamp_format
            )
        )

        # Calculate the time until the event
        replacement_strings["event_timestamp_countdown"] = (
            starting_epoch_timestamp - event_epoch_timestamp
        )
        replacement_strings["event_timestamp_countdown_rolling"] = (
            f"%{{pts\\:hms\\:{replacement_strings['event_timestamp_countdown']}}}"
        )

    replacement_strings["event_city"] = event_info.event_metadata.city or "n/a"
    replacement_strings["event_street"] = event_info.event_metadata.street or "n/a"
    replacement_strings["event_reason"] = event_info.event_metadata.reason or "n/a"
    replacement_strings["event_latitude"] = event_info.event_metadata.latitude or 0.0
    replacement_strings["event_longitude"] = event_info.event_metadata.longitude or 0.0

    try:
        # Try to replace strings!
        user_formatted_text = user_formatted_text.format(**replacement_strings)
    except KeyError as e:
        user_formatted_text = f"Bad string format: Invalid variable {str(e)}"
        _LOGGER.warning(user_formatted_text)

    # Escape characters ffmpeg needs
    user_formatted_text = escape_drawtext_literals(user_formatted_text)
    user_formatted_text = user_formatted_text.replace("\\n", os.linesep)

    ffmpeg_text = ffmpeg_text.replace("__USERTEXT__", user_formatted_text)

    ffmpeg_base: str = (
        black_base
        + black_size.format(
            width=video_layout.video_width, height=video_layout.video_height
        )
        + "[base]"
    )

    ffmpeg_filter: str = ffmpeg_base.format(
        duration=clip_duration, speed=video_settings["movie_speed"]
    )

    # Add the respective camera filters.
    for ffmpeg_camera_filter in ffmpeg_camera_filters:
        ffmpeg_filter += ffmpeg_camera_filter

    # Add the respective camera positions.
    ffmpeg_position: str = ""
    for ffmpeg_camera_position in ffmpeg_camera_positions:
        ffmpeg_position += ffmpeg_camera_position

    ffmpeg_filter += (
        ffmpeg_position
        + ffmpeg_text
        + video_settings["ffmpeg_speed"].format(input_clip=input_clip)
        + video_settings["ffmpeg_motiononly"].format(input_clip=input_clip)
        + video_settings["ffmpeg_hwupload"].format(input_clip=input_clip)
    )

    title_timestamp: str = str(
        replacement_strings["event_timestamp"]
        if event_info.event_metadata.reason == "SENTRY"
        and replacement_strings["event_timestamp"] != "n/a"
        else replacement_strings["start_timestamp"]
    )
    title: str = (
        f"{replacement_strings['event_reason']}: {title_timestamp}"
        if replacement_strings["event_reason"] != "n/a"
        else title_timestamp
    )

    ffmpeg_metadata: list[str] = [
        "-metadata",
        f"creation_time={
            starting_timestamp.astimezone(timezone.utc).strftime(
                '%Y-%m-%dT%H:%M:%S.000000Z'
            )
        }",
        "-metadata",
        f"description=Created by tesla_dashcam {VERSION_STR}",
        "-metadata",
        f"title={title}",
    ]

    ffmpeg_command: list[str] = (
        [video_settings["ffmpeg_exec"]]
        + ["-loglevel", "info"]
        + video_settings["ffmpeg_hwdev"]
        + video_settings["ffmpeg_hwout"]
    )

    ffmpeg_command.extend(ffmpeg_camera_commands)

    ffmpeg_command += (
        ["-filter_complex", ffmpeg_filter]
        + ["-map", f"[{video_settings['input_clip']}]"]
        + video_settings["other_params"]
        + ffmpeg_metadata
    )

    ffmpeg_command = ffmpeg_command + ["-y", temp_movie_name]
    _LOGGER.debug("FFMPEG Command: %s", ffmpeg_command)

    # Run the command.
    try:
        ffmpeg_output = run(ffmpeg_command, capture_output=True, check=True, text=True)
    except CalledProcessError as exc:
        print(
            f"{get_current_timestamp()}\t\t\tError trying to create clip for "
            f"{
                os.path.join(
                    event_info.folder,
                    local_timestamp.strftime('%Y-%m-%dT%H-%M-%S') + '.mp4',
                )
            }."
            f"RC: {exc.returncode}\n"
            f"{get_current_timestamp()}\t\t\tCommand: {exc.cmd}\n"
            f"{get_current_timestamp()}\t\t\tError: {exc.stderr}\n\n"
        )
        return False
    if FFMPEG_DEBUG:
        _LOGGER.debug("FFMPEG output:\n %s", ffmpeg_output.stdout)
        _LOGGER.debug("FFMPEG stderr output:\n %s", ffmpeg_output.stderr)

    clip_info.filename = temp_movie_name
    clip_info.start_timestamp = starting_timestamp
    clip_info.end_timestamp = ending_timestamp
    # Get actual duration of our new video, required for chapters when concatenating.
    if metadata := get_metadata(video_settings["ffmpeg_exec"], [temp_movie_name]):
        clip_info.duration = metadata[0].duration
        clip_info.video_metadata = metadata[0]

    return True


def create_title_screen(
    events: list[Event], video_settings: dict[str, Any]
) -> Image | None:
    """Create a map centered around the event"""
    _LOGGER.debug("Creating map based on %d event.", len(events))
    if len(events) == 0:
        _LOGGER.debug("No events provided to create map for.")
        return None

    m = staticmap.StaticMap(
        video_settings["video_layout"].video_width,
        video_settings["video_layout"].video_height,
    )

    coordinates: list[tuple[float, float]] = []
    for event in events:
        if not event.event_metadata.longitude or not event.event_metadata.latitude:
            continue

        try:
            lon: float = float(event.event_metadata.longitude)
        except (ValueError, TypeError) as exc:
            _LOGGER.debug(
                "Error trying to convert longitude (%s) into a float. exc: %s",
                event.event_metadata.longitude,
                exc,
            )
            continue

        try:
            lat: float = float(event.event_metadata.latitude)
        except (ValueError, TypeError) as exc:
            _LOGGER.debug(
                "Error trying to convert latitude (%s) into a float. exc: %s",
                event.event_metadata.latitude,
                exc,
            )
            continue

        # Sometimes event info has a very small (i.e. 2.35754e-311) or 0 value, we
        # ignore if both are 0.
        # 0,0 is in the ocean near Africa.
        if round(lon, 5) == 0 and round(lat, 5) == 0:
            _LOGGER.debug(
                "Skipping as longitude %s and/or latidude %s are invalid.", lon, lat
            )
            continue

        coordinate: tuple[float, float] = (lon, lat)
        coordinates.append(coordinate)

        # Add marker for each point
        # Marker outline
        m.add_marker(staticmap.CircleMarker(coordinate, "white", 18))
        # Marker
        m.add_marker(staticmap.CircleMarker(coordinate, "#0036FF", 12))

    if len(coordinates) == 0:
        _LOGGER.debug("No valid coordinates found within the events.")
        return None
    # Only create line if we have more then 1 coordinate
    elif len(coordinates) > 1:
        # Line outline
        m.add_line(staticmap.Line(coordinates, "white", 18))
        # Line
        m.add_line(staticmap.Line(coordinates, "#0036FF", 12))

    image = m.render()

    return image


def create_movie(
    movie: Event | Movie,
    event_info: list[Event],
    movie_filename: str,
    video_settings: dict[str, Any],
    chapter_offset: int,
    title_screen_map: bool,
):
    """Concatenate provided movie files into 1."""
    # Just return if there are no clips.
    if movie.count <= 0:
        _LOGGER.debug("Movie list is empty")
        return False

    # Determine the scale of the video, for now this is based on the largest video
    # in the list.
    movie_scale = SimpleNamespace(
        width=video_settings["video_layout"].video_width,
        height=video_settings["video_layout"].video_height,
    )
    movie_scale.width = movie.width
    movie_scale.height = movie.height

    title_video_filename: str | None = None
    title_image_filename: str | None = None
    file_content: list[SimpleNamespace] = []
    meta_start: int = 0
    total_videoduration: int = 0
    ffmpeg_params: list[str] = []
    if title_screen_map:
        if (
            title_image := create_title_screen(
                events=event_info, video_settings=video_settings
            )
        ) is not None:
            _, title_image_filename = mkstemp(suffix=".png", text=False)

            try:
                title_image.save(title_image_filename)
            except (ValueError, OSError) as exc:
                print(
                    f"{get_current_timestamp()}\t\t\tError trying to save title image. "
                    f"RC: {str(exc)}"
                )
                title_image_filename = None
            else:
                _LOGGER.debug("Title image saved to %s", title_image_filename)

        if title_image_filename is not None:
            _, title_video_filename = mkstemp(suffix=".mp4", text=False)
            _LOGGER.debug("Creating movie for title image to %s", title_video_filename)
            ffmpeg_params = [
                "-loop",
                "1",
                "-framerate",
                # "1/3",
                str(video_settings["fps"]),
                "-t",
                "3",
                "-i",
                title_image_filename,
                "-vf",
                f"fps={video_settings['fps']},"
                f"scale={movie_scale.width}x{movie_scale.height}",
                "-pix_fmt",
                "yuv420p",
            ]

            ffmpeg_command: list[str] = (
                [video_settings["ffmpeg_exec"]]
                + ["-loglevel", "info"]
                + video_settings["ffmpeg_hwdev"]
                + video_settings["ffmpeg_hwout"]
                + ffmpeg_params
                + video_settings["other_params"]
            )

            ffmpeg_command = ffmpeg_command + ["-y", title_video_filename]

            _LOGGER.debug("FFMPEG Command: %s", ffmpeg_command)
            try:
                ffmpeg_output = run(
                    ffmpeg_command,
                    capture_output=True,
                    check=True,
                    text=True,
                )
            except CalledProcessError as exc:
                print(
                    f"{get_current_timestamp()}\t\t\tError trying to create title clip."
                    f" RC: {exc.returncode}\n"
                    f"{get_current_timestamp()}\t\t\tCommand: {exc.cmd}\n"
                    f"{get_current_timestamp()}\t\t\tError: {exc.stderr}\n\n"
                )
                title_video_filename = None

            else:
                if FFMPEG_DEBUG:
                    _LOGGER.debug("FFMPEG output:\n %s", ffmpeg_output.stdout)
                    _LOGGER.debug("FFMPEG stderr output:\n %s", ffmpeg_output.stderr)
                file_content = [
                    SimpleNamespace(
                        filename=title_video_filename,
                        width=movie_scale.width,
                        height=movie_scale.height,
                    )
                ]
                total_videoduration += 3 * 1000000000
                meta_start += 3 * 1000000000 + 1

            # Now remove the title image
            try:
                os.remove(title_image_filename)
            except (OSError, IOError):
                _LOGGER.debug("Failed to remove %s", title_image_filename)

    # Go through the list of clips to create the command and content for
    # chapter meta file.
    total_clips: int = 0
    meta_content: str = ""
    start_timestamp: datetime = datetime.max.replace(tzinfo=get_localzone())
    end_timestamp: datetime = datetime.min.replace(tzinfo=get_localzone())
    chapter_offset = chapter_offset * 1000000000
    complex_concat: bool = False
    ffmpeg_params = []

    # Loop through the list sorted by video timestamp.
    for video_clip in movie.items_sorted:
        # Check that this item was included for processing or not.
        if video_clip.filename is None:
            continue

        if not os.path.isfile(video_clip.filename):
            print(
                f"{get_current_timestamp()}\t\tFile {video_clip.filename} does not "
                "exist anymore, skipping."
            )
            continue
        _LOGGER.debug(
            "Video file %s will be added to %s", video_clip.filename, movie_filename
        )

        # Check if this video has to be re-scaled.
        if (
            video_clip.width != movie_scale.width
            or video_clip.height != movie_scale.height
        ):
            _LOGGER.debug(
                "Video %s will be rescaled from %dx%d to %dx%d",
                video_clip.filename,
                video_clip.width,
                video_clip.height,
                movie_scale.width,
                movie_scale.height,
            )
            complex_concat = True

        # Add file information to our list.
        file_content.append(
            SimpleNamespace(
                filename=video_clip.filename,
                width=video_clip.width,
                height=video_clip.height,
            )
        )

        total_clips = total_clips + 1
        title_dt: datetime = video_clip.start_timestamp.astimezone(get_localzone())

        # For duration need to also calculate if video was sped-up or slowed down.
        video_duration = int(video_clip.duration * 1000000000)
        total_videoduration += video_duration
        chapter_start = meta_start
        if video_duration > abs(chapter_offset):
            if chapter_offset < 0:
                chapter_start = meta_start + video_duration + chapter_offset
            elif chapter_offset > 0:
                chapter_start = chapter_start + chapter_offset

        # We need to add an initial chapter if our "1st" chapter is not at the
        # beginning of the movie.
        if total_clips == 1 and chapter_start > 0:
            meta_content = (
                "[CHAPTER]{linesep}"
                "TIMEBASE=1/1000000000{linesep}"
                "START={start}{linesep}"
                "END={end}{linesep}"
                "title={title}{linesep}".format(
                    linesep=os.linesep, start=0, end=chapter_start - 1, title="Start"
                )
            )

        meta_content = (
            meta_content + f"[CHAPTER]{os.linesep}"
            f"TIMEBASE=1/1000000000{os.linesep}"
            f"START={chapter_start}{os.linesep}"
            f"END={meta_start + video_duration}{os.linesep}"
            f"title={title_dt.strftime(video_settings['timestamp_format'])}{os.linesep}"
        )
        meta_start = meta_start + 1 + video_duration

        start_timestamp = (
            video_clip.start_timestamp
            if start_timestamp > video_clip.start_timestamp
            else start_timestamp
        )

        end_timestamp = (
            video_clip.end_timestamp
            if end_timestamp < video_clip.end_timestamp
            else end_timestamp
        )

    if total_clips == 0:
        print(f"{get_current_timestamp()}\t\tError: No valid clips to merge found.")
        return False

    # Write out the meta data file.
    meta_content = ";FFMETADATA1" + os.linesep + meta_content
    ffmpeg_meta_filehandle, ffmpeg_meta_filename = mkstemp(suffix=".txt", text=True)
    with os.fdopen(ffmpeg_meta_filehandle, "w") as fp:
        fp.write(meta_content)

    _LOGGER.debug("Meta file contains:\n%s", meta_content)

    if video_settings["movflags_faststart"]:
        ffmpeg_params = ffmpeg_params + ["-movflags", "+faststart"]

    user_timestamp_format = video_settings["timestamp_format"]
    if len(event_info) == 1:
        title_timestamp = (
            event_info[0]
            .event_metadata.timestamp.astimezone(get_localzone())
            .strftime(user_timestamp_format)
            if event_info[0].event_metadata.reason == "SENTRY"
            and event_info[0].event_metadata.timestamp
            else start_timestamp.astimezone(get_localzone()).strftime(
                user_timestamp_format
            )
        )
        title: str = (
            f"{event_info[0].event_metadata.reason or title_timestamp}: "
            f"{title_timestamp}"
        )
    else:
        title = (
            f"{
                start_timestamp.astimezone(get_localzone()).strftime(
                    user_timestamp_format
                )
            } - "
            f"{
                end_timestamp.astimezone(get_localzone()).strftime(
                    user_timestamp_format
                )
            }"
        )

    ffmpeg_metadata = [
        "-metadata",
        f"creation_time={
            start_timestamp.astimezone(timezone.utc).strftime(
                '%Y-%m-%dT%H:%M:%S.000000Z'
            )
        }",
        "-metadata",
        f"description=Created by tesla_dashcam {VERSION_STR}",
        "-metadata",
        f"title={title}",
    ]

    # Go through the events and add the 1st valid coordinations for location to metadata
    for event in event_info:
        if (
            event.event_metadata.longitude is None
            or event.event_metadata.latitude is None
        ):
            continue

        try:
            lon = float(event.event_metadata.longitude)
            lat = float(event.event_metadata.latitude)
        except (ValueError, TypeError) as exc:
            _LOGGER.debug(
                "Error trying to convert longitude/latitude (%s, %s) into a float. "
                "exc: %s",
                event.event_metadata.longitude,
                event.event_metadata.latitude,
                exc,
            )
        else:
            # Sometimes event info has a very small (i.e. 2.35754e-311) or 0 value, we
            # ignore if both are 0.
            # 0,0 is in the ocean near Africa.
            if round(lon, 5) == 0 and round(lat, 5) == 0:
                _LOGGER.debug(
                    "Skipping as longitude %s and/or latidude %s are invalid.",
                    lon,
                    lat,
                )
                continue

            location = f"{lat:+.4f}{lon:+.4f}"
            ffmpeg_metadata.extend(
                [
                    "-metadata",
                    f"location={location}",
                    "-metadata",
                    f"location-eng={location}",
                ]
            )
            break

    # Now start creating the movie.
    movie_file_created: bool = False
    try:
        ffmpeg_output = create_movie_ffmpeg(
            movie_filename=movie_filename,
            video_settings=video_settings,
            movie_scale=movie_scale,
            ffmpeg_params=ffmpeg_params,
            complex_concat=complex_concat,
            file_content=file_content,
            ffmpeg_meta_filename=ffmpeg_meta_filename,
            ffmpeg_metadata=ffmpeg_metadata,
        )
    except CalledProcessError as outer_exc:
        # Creation failed, if we were doing simple concat then try complex now instead.
        if not complex_concat:
            # Try with ffmpeg_complex instead.
            _LOGGER.debug(
                "Creating movie %s failed using simple concatenation, using complex "
                "concatenation instead.",
                movie_filename,
            )
            try:
                ffmpeg_output = create_movie_ffmpeg(
                    movie_filename=movie_filename,
                    video_settings=video_settings,
                    movie_scale=movie_scale,
                    ffmpeg_params=ffmpeg_params,
                    complex_concat=True,
                    file_content=file_content,
                    ffmpeg_meta_filename=ffmpeg_meta_filename,
                    ffmpeg_metadata=ffmpeg_metadata,
                )
            except CalledProcessError as inner_exc:
                print(
                    f"{get_current_timestamp()}\t\t\tError trying to create movie "
                    f"{movie_filename}. RC: {inner_exc.returncode}\n"
                    f"{get_current_timestamp()}\t\t\tCommand: {inner_exc.cmd}\n"
                    f"{get_current_timestamp()}\t\t\tError: {inner_exc.stderr}\n\n"
                )
            else:
                # Using complex concatenation instead worked.
                movie_file_created = True
        else:
            print(
                f"{get_current_timestamp()}\t\t\tError trying to create movie "
                f"{movie_filename}. RC: {outer_exc.returncode}\n"
                f"{get_current_timestamp()}\t\t\tCommand: {outer_exc.cmd}\n"
                f"{get_current_timestamp()}\t\t\tError: {outer_exc.stderr}\n\n"
            )
    else:
        movie_file_created = True

    # If we were able to create the movie file then get data and perform some additional
    # post-processing.
    if movie_file_created:
        movie.filename = movie_filename
        movie.start_timestamp = start_timestamp
        movie.end_timestamp = end_timestamp
        # Get actual duration of our new video, required for chapters when concatenating
        metadata = get_metadata(video_settings["ffmpeg_exec"], [movie_filename])
        if metadata:
            movie.duration = metadata[0].duration
            movie.video_metadata = metadata[0]

        # Set the file timestamp if to be set based on timestamp event
        if video_settings["set_moviefile_timestamp"] != "RENDER":
            moviefile_timestamp = start_timestamp.astimezone(get_localzone())
            if video_settings["set_moviefile_timestamp"] == "STOP":
                moviefile_timestamp = end_timestamp.astimezone(get_localzone())
            elif (
                video_settings["set_moviefile_timestamp"] == "SENTRY"
                and len(event_info) == 1
                and event_info[0].event_metadata.timestamp is not None
            ):
                moviefile_timestamp = event_info[0].event_metadata.timestamp.astimezone(
                    get_localzone()
                )

            _LOGGER.debug(
                "Setting timestamp for movie file %s to %s ",
                movie_filename,
                moviefile_timestamp.strftime("%Y-%m-%dT%H-%M-%S"),
            )
            moviefile_unix_timestamp: float = mktime(moviefile_timestamp.timetuple())
            os.utime(
                movie_filename, (moviefile_unix_timestamp, moviefile_unix_timestamp)
            )

    # Remove temp join file.
    try:
        os.remove(ffmpeg_meta_filename)
    except (OSError, IOError) as exc:
        _LOGGER.debug("Failed to remove %s: %s", ffmpeg_meta_filename, exc)

    # Remove title video temp file
    if title_video_filename:
        try:
            os.remove(title_video_filename)
        except (OSError, IOError) as exc:
            _LOGGER.debug("Failed to remove %s: %s", title_video_filename, exc)

    if movie.filename is None:
        return False

    return True


def create_movie_ffmpeg(
    movie_filename: str,
    video_settings: dict[str, Any],
    movie_scale: SimpleNamespace,
    ffmpeg_params: list[str],
    complex_concat,
    file_content: list[SimpleNamespace],
    ffmpeg_meta_filename: str,
    ffmpeg_metadata: list[str],
) -> CompletedProcess[str]:
    chapter_file: int = 1
    metadata_file_index: int = 1
    ffmpeg_join_filename: str | None = None
    video_string: str = ""
    ffmpeg_complex: str = ""
    file_content_string: str = ""
    ffmpeg_params_files: list[str] = []
    for file_number, video_file in enumerate(file_content):
        if complex_concat:
            # We need to do a complex concatenation.
            ffmpeg_scale: str = ""
            if (
                video_file.width != movie_scale.width
                or video_file.height != movie_scale.height
            ):
                # This video needs to be rescaled.
                ffmpeg_scale = (
                    f"scale={movie_scale.width}:{movie_scale.height}:"
                    "force_original_aspect_ratio=decrease,"
                    f"pad={movie_scale.width}:{movie_scale.height}:"
                    f"({movie_scale.width}-iw)/2:"
                    f"({movie_scale.height}-ih)/2:black,"
                )

            ffmpeg_complex += (
                f"[{file_number}:v]{ffmpeg_scale}setpts=PTS-STARTPTS, "
                f"setsar=1[v{file_number}];"
            )
            ffmpeg_params_files.extend(
                [
                    "-i",
                    video_file.filename.strip(),
                ]
            )
            video_string += f"[v{file_number}]"

        else:
            # We're doing simple concatenation.
            ffmpeg_complex += f"[{file_number}:v]setpts=PTS-STARTPTS[v{file_number}];"
            # Add this file in our join list.
            # NOTE: Recent ffmpeg changes requires Windows paths in this file to look
            # like file 'file:<actual path>'
            # https://trac.ffmpeg.org/ticket/2702
            # Write out the video files file
            # Escape single quotes in file paths per ffmpeg concat syntax
            join_path = video_file.filename.strip().replace(os.sep, "/")
            join_path = join_path.replace("'", "'\\''")
            file_content_string += f"file '{join_path}'" + os.linesep

    if complex_concat:
        # Final items to be added for a complex concatenation.
        _LOGGER.debug("Using ffmpeg complex for %s", movie_filename)
        ffmpeg_params_files.extend(
            [
                "-f",
                "ffmetadata",
                "-i",
                ffmpeg_meta_filename,
            ]
        )
        chapter_file = len(file_content)
        metadata_file_index = chapter_file
        ffmpeg_params_files.extend(
            [
                "-filter_complex",
                (
                    f"{ffmpeg_complex}{video_string}concat=n={len(file_content)}"
                    ":v=1:a=0[outv]"
                ),
                "-map",
                "[outv]",
            ]
        )
        # Complex concat re-encodes; apply encoder/quality and hardware
        # acceleration flags here via other_params.
        ffmpeg_params_files += video_settings["other_params"]
    else:
        # Final items to be added for a simple concatenation.
        _LOGGER.debug(
            "Using concat demuxer as no video rescaling is required for %s",
            movie_filename,
        )
        ffmpeg_params_files = [
            "-f",
            "concat",
            "-safe",
            "0",
            "-xerror",
        ]

        _LOGGER.debug("Video file contains:\n%s", file_content_string)
        ffmpeg_join_filehandle, ffmpeg_join_filename = mkstemp(suffix=".txt", text=True)
        with os.fdopen(ffmpeg_join_filehandle, "w") as fp:
            fp.write(file_content_string)

        ffmpeg_params_files.extend(
            [
                "-i",
                ffmpeg_join_filename,
                "-f",
                "ffmetadata",
                "-i",
                ffmpeg_meta_filename,
            ]
        )

        # Stream copy to avoid re-encoding when using concat demuxer
        ffmpeg_params_files.extend(["-c", "copy"])

    ffmpeg_params_files.extend(
        [
            "-map_metadata",
            f"{metadata_file_index}",
            "-map_chapters",
            f"{chapter_file}",
        ]
    )

    ffmpeg_command = (
        [video_settings["ffmpeg_exec"]]
        + ["-loglevel", "info"]
        + video_settings["ffmpeg_hwdev"]
        + video_settings["ffmpeg_hwout"]
        + ffmpeg_params_files
        + ffmpeg_params
        + ffmpeg_metadata
        + ["-y", movie_filename]
    )

    _LOGGER.debug("FFMPEG Command: %s", ffmpeg_command)
    try:
        ffmpeg_output = run(ffmpeg_command, capture_output=True, check=True, text=True)
    except CalledProcessError:
        # Remove temp join file.
        if ffmpeg_join_filename is not None:
            try:
                os.remove(ffmpeg_join_filename)
            except (OSError, IOError) as cleanup_exc:
                _LOGGER.debug(
                    "Failed to remove %s: %s", ffmpeg_join_filename, cleanup_exc
                )
        raise

    if FFMPEG_DEBUG:
        _LOGGER.debug("FFMPEG output:\n %s", ffmpeg_output.stdout)
        _LOGGER.debug("FFMPEG stderr output:\n %s", ffmpeg_output.stderr)

    # Remove temp join file.
    if ffmpeg_join_filename is not None:
        try:
            os.remove(ffmpeg_join_filename)
        except (OSError, IOError) as exc:
            _LOGGER.debug("Failed to remove %s: %s", ffmpeg_join_filename, exc)

    return ffmpeg_output


def make_folder(parameter: str, folder: str) -> bool:
    # Create folder if not already existing.
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        print(
            f"{get_current_timestamp()}Error creating folder {folder} for parameter "
            f"{parameter}"
        )
        return False

    return True


def delete_intermediate(movie_files: list[str]) -> None:
    """Delete the files provided in list"""
    for file in movie_files:
        if file is not None:
            if os.path.isfile(file):
                _LOGGER.debug("Deleting file %s.", file)
                try:
                    os.remove(file)
                except (OSError, IOError) as exc:
                    print(
                        f"{get_current_timestamp()}\t\tError trying to remove file "
                        f"{file}: {exc}"
                    )
            elif os.path.isdir(file):
                _LOGGER.debug("Deleting folder %s.", file)
                # This is more specific for Mac but won't hurt on other platforms.
                if os.path.exists(os.path.join(file, ".DS_Store")):
                    try:
                        os.remove(os.path.join(file, ".DS_Store"))
                    except (OSError, IOError) as exc:
                        _LOGGER.debug(
                            "Failed to remove .DS_Store from %s: %s", file, exc
                        )

                try:
                    os.rmdir(file)
                except (OSError, IOError) as exc:
                    print(
                        f"{get_current_timestamp()}\t\tError trying to remove folder "
                        f"{file}: {exc}"
                    )


def process_folders(
    source_folders: list[str], video_settings: dict[str, Any], delete_source: bool
) -> None:
    """Process all clips found within folders."""

    # Retrieve all the video files within the folders provided.
    event_list: dict[str, Event] = get_movie_files(source_folders, video_settings)

    if event_list is None:
        print(f"{get_current_timestamp()}No video files found to process.")
        return

    start_time: float = timestamp()

    total_clips: int = sum(event.count for event in event_list.values())
    print(
        f"{get_current_timestamp()}There are {len(event_list)} event folder(s) with "
        f"{total_clips} clips to process."
    )

    # Loop through all the events (folders) sorted.
    movies: dict[str, Movie] = {}
    merge_group_template: str | None = video_settings["merge_group_template"]
    timestamp_format: str = video_settings["merge_timestamp_format"]

    event_folder: str
    for event_count, event_folder in enumerate(sorted(event_list)):
        event_info: Event = event_list[event_folder]

        # Get the start and ending timestamps, we add duration to
        # last timestamp to get true ending.
        first_clip_tmstp: datetime = event_info.start_timestamp
        last_clip_tmstp: datetime = event_info.end_timestamp

        _LOGGER.debug(
            f"Processing folder {event_folder}: first_clip={first_clip_tmstp}, last_clip={last_clip_tmstp}"
        )
        if video_settings["start_timestamp"] is not None:
            _LOGGER.debug(
                f"  Comparing last_clip {last_clip_tmstp} < start_timestamp {video_settings['start_timestamp']}"
            )

        # Skip this folder if we it does not fall within provided timestamps.
        if (
            video_settings["start_timestamp"] is not None
            and last_clip_tmstp < video_settings["start_timestamp"]
        ):
            # Clips from this folder are from before start timestamp requested.
            _LOGGER.debug(
                "Clips in folder end at %s which is still before start timestamp %s",
                last_clip_tmstp,
                video_settings["start_timestamp"],
            )
            continue

        if (
            video_settings["end_timestamp"] is not None
            and first_clip_tmstp > video_settings["end_timestamp"]
        ):
            # Clips from this folder are from after end timestamp requested.
            _LOGGER.debug(
                "Clips in folder start at %s which is after end timestamp %s",
                first_clip_tmstp,
                video_settings["end_timestamp"],
            )
            continue

        # No processing, add to list of movies to merge if what was provided is just a
        # file
        if event_info.isfile:
            key: str = event_info.template(
                merge_group_template, timestamp_format, video_settings
            )
            movies.setdefault(key, Movie()).set_event(event_info)
            continue

        _LOGGER.debug(
            "Processing event with start timestamp %s and end timestamp %s",
            first_clip_tmstp,
            last_clip_tmstp,
        )

        # Determine the starting and ending timestamps for the clips in this folder
        # based on start/end timestamps provided and offsets.
        # If set for Sentry then offset is only used for clips with reason Sentry and
        # having a event timestamp.
        start_offset: int | None = None
        end_offset: int | None = None
        offset_start_timestamp: datetime = first_clip_tmstp
        offset_end_timestamp: datetime = last_clip_tmstp

        # Determine offset to use.
        if (
            event_info.event_metadata.reason == "SENTRY"
            and event_info.event_metadata.timestamp is not None
        ):
            # This is a sentry event and we have an event timestamp.

            # Are either --sentry_start_offset or --sentry_end_offset provided?
            if (
                video_settings["sentry_start_offset"] is not None
                or video_settings["sentry_end_offset"] is not None
            ):
                # They were, start and end offset are set to their values.
                start_offset = video_settings["sentry_start_offset"]
                end_offset = video_settings["sentry_end_offset"]
                offset_start_timestamp = event_info.event_metadata.timestamp
                offset_end_timestamp = event_info.event_metadata.timestamp
                _LOGGER.debug(
                    "Offsets based on sentry event with sentry start offset %d, sentry "
                    "end offset %s and sentry event timestamp %s",
                    start_offset,
                    end_offset,
                    offset_start_timestamp,
                )
            elif video_settings["sentry_offset"]:
                # Otherwise, was it set to use
                # with the --sentry_offset legacy parameter?
                start_offset = video_settings["start_offset"] or 60
                end_offset = video_settings["end_offset"] or 30
                offset_start_timestamp = event_info.event_metadata.timestamp
                offset_end_timestamp = event_info.event_metadata.timestamp
                _LOGGER.debug(
                    "Offsets for sentry event based on standard offsets with start "
                    "offset %d, end offset %d and sentry event timestamp %s",
                    start_offset,
                    end_offset,
                    offset_start_timestamp,
                )

        # Do we not yet have a start_offset but --start_offset was provided?
        if start_offset is None and video_settings["start_offset"] is not None:
            # We do, then it means we're going to use that.
            start_offset = video_settings["start_offset"] or 0
            # Set offset timestamp to start if offset is positive otherwise to end.
            offset_start_timestamp = (
                first_clip_tmstp if start_offset >= 0 else last_clip_tmstp
            )
            _LOGGER.debug(
                "Starting offset %d and timestamp %s",
                start_offset,
                offset_start_timestamp,
            )

        # Do we not yet have a start_offset but --start_offset was provided?
        if end_offset is None and video_settings["end_offset"] is not None:
            # We do, then it means we're going to use that.
            end_offset = video_settings["end_offset"] or 0
            # Set offset timestamp to start if offset is positive otherwise to end.
            offset_end_timestamp = (
                first_clip_tmstp if end_offset >= 0 else last_clip_tmstp
            )
            _LOGGER.debug(
                "Ending offset %s and timestamp %s", end_offset, offset_end_timestamp
            )

        event_start_timestamp: datetime = (
            offset_start_timestamp + timedelta(seconds=start_offset)
            if start_offset is not None
            else first_clip_tmstp
        )
        event_end_timestamp: datetime = (
            offset_end_timestamp + timedelta(seconds=end_offset)
            if end_offset is not None
            else last_clip_tmstp
        )

        if event_start_timestamp != first_clip_tmstp:
            _LOGGER.debug(
                "Clip starting timestamp changed to %s from %s due to start offset %s "
                "and offset timestamp %s",
                event_start_timestamp,
                first_clip_tmstp,
                start_offset,
                offset_start_timestamp,
            )

        if event_end_timestamp != last_clip_tmstp:
            _LOGGER.debug(
                "Clip ending timestamp changed to %s from %s due to end offset %s "
                "and offset timestamp %s",
                event_end_timestamp,
                last_clip_tmstp,
                end_offset,
                offset_end_timestamp,
            )

        # Make sure that our event start timestamp is not after our end timestamp
        if event_start_timestamp > event_end_timestamp:
            # Start timestamp is greater then end timestamp, we'll switch them
            _LOGGER.debug(
                "Clip start timestamp %s was after clip end timestamp %s, swapping "
                "them.",
                event_start_timestamp,
                event_end_timestamp,
            )
            event_start_timestamp, event_end_timestamp = (
                event_end_timestamp,
                event_start_timestamp,
            )

        # Make sure that our event start timestamp is equal to or after
        # our clip start timestamp and before our event end timestamp.
        if not (first_clip_tmstp <= event_start_timestamp <= last_clip_tmstp):
            # Event start timestamp is either before clip start timestamp or
            # after clip end timestamp
            # Setting it back to clip start timestamp
            event_start_timestamp = first_clip_tmstp
            _LOGGER.debug(
                "Clip start timestamp changed back to %s as updated offset timestamp "
                "was before clip start timestamp or after clip end timestamp",
                first_clip_tmstp,
            )

        # Make sure that our event end timestamp is equal to or after
        # our clip start timestamp and before our event end timestamp.
        if not (first_clip_tmstp <= event_end_timestamp <= last_clip_tmstp):
            # Event end timestamp is either before clip start timestamp or
            # after clip end timestamp
            # Setting it back to clip end timestamp
            event_end_timestamp = last_clip_tmstp
            _LOGGER.debug(
                "Clip end timestamp changed back to %s as updated offset timestamp "
                "was before clip start timestamp or after clip end timestamp",
                last_clip_tmstp,
            )

        # Clamp event timestamps to user-requested start/end timestamp window
        if video_settings["start_timestamp"] is not None:
            _LOGGER.debug(
                f"Comparing event_start_timestamp {event_start_timestamp} < user start {video_settings['start_timestamp']}"
            )
            if event_start_timestamp < video_settings["start_timestamp"]:
                _LOGGER.debug(
                    "Clip start timestamp changed from %s to %s to match "
                    "user-requested start timestamp",
                    event_start_timestamp,
                    video_settings["start_timestamp"],
                )
                event_start_timestamp = video_settings["start_timestamp"]

        if video_settings["end_timestamp"] is not None:
            _LOGGER.debug(
                f"Comparing event_end_timestamp {event_end_timestamp} > user end {video_settings['end_timestamp']}"
            )
            if event_end_timestamp > video_settings["end_timestamp"]:
                _LOGGER.debug(
                    "Clip end timestamp changed from %s to %s to match "
                    "user-requested end timestamp",
                    event_end_timestamp,
                    video_settings["end_timestamp"],
                )
                event_end_timestamp = video_settings["end_timestamp"]

        # Put them together to create the filename for the folder.
        event_movie_filename = (
            event_start_timestamp.astimezone(get_localzone()).strftime(
                "%Y-%m-%dT%H-%M-%S"
            )
            + "_"
            + event_end_timestamp.astimezone(get_localzone()).strftime(
                "%Y-%m-%dT%H-%M-%S"
            )
        )

        # Now add full path to it.
        event_movie_filename = (
            os.path.join(video_settings["target_folder"], event_movie_filename) + ".mp4"
        )

        # Do not process the files from this folder if we're to skip it if
        # the target movie file already exist.
        if video_settings["skip_existing"] and os.path.isfile(event_movie_filename):
            print(
                f"{get_current_timestamp()}\tSkipping folder {event_folder} as "
                f"{event_movie_filename} is already created "
                f"({event_count + 1}/{len(event_list)})"
            )

            # Get actual duration of our new video, required for chapters when
            # concatenating.
            event_info.filename = event_movie_filename
            event_info.start_timestamp = event_start_timestamp
            event_info.end_timestamp = event_end_timestamp
            metadata: list[Video_Metadata] = get_metadata(
                video_settings["ffmpeg_exec"], [event_movie_filename]
            )
            if metadata:
                event_info.duration = metadata[0].duration
                event_info.video_metadata = metadata[0]

            key = event_info.template(
                merge_group_template, timestamp_format, video_settings
            )
            movies.setdefault(key, Movie()).set_event(event_info)
            movies.setdefault(key, Movie()).video_metadata = metadata[0]
            continue

        print(
            f"{get_current_timestamp()}\tProcessing {event_info.count} clips in folder "
            f"{event_folder} ({event_count + 1}/{len(event_list)})"
        )

        # Loop through all the clips within the event.
        delete_folder_clips: list[str] = []
        delete_folder_files: bool = delete_source
        delete_file_list: list[str] = []

        for clip_number, clip_timestamp in enumerate(event_info.sorted):
            if (clip_info := event_info.clip(clip_timestamp)) is None:
                _LOGGER.warning(
                    "Clip %s in folder %s is not valid, skipping.",
                    clip_timestamp,
                    event_folder,
                )
                continue

            if create_intermediate_movie(
                event_info,
                clip_info,
                (event_start_timestamp, event_end_timestamp),
                video_settings,
                clip_number,
            ):
                if (
                    clip_info.filename is not None
                    and clip_info.filename != event_info.filename
                ):
                    delete_folder_clips.append(clip_info.filename)

                # Add the files to our list for removal.
                for _, camera_info in clip_info.cameras:
                    delete_file_list.append(
                        os.path.join(event_folder, camera_info.filename)
                    )
            else:
                delete_folder_files = False

        # All clips for the event  have been processed, merge those clips
        # together now.
        print(
            f"{get_current_timestamp()}\t\tCreating movie {event_movie_filename}, "
            "please be patient."
        )

        if create_movie(
            event_info,
            [event_info],
            event_movie_filename,
            video_settings,
            0,
            video_settings["video_layout"].title_screen_map,
        ):
            if event_info.filename is not None:
                key = event_info.template(
                    merge_group_template, timestamp_format, video_settings
                )
                movies.setdefault(key, Movie()).set_event(event_info)

                print(
                    f"{get_current_timestamp()}\tMovie {event_info.filename} for "
                    f"folder {event_folder} with "
                    f"duration {str(timedelta(seconds=int(event_info.duration)))} is "
                    "ready."
                )

                # Delete the intermediate files we created.
                if not video_settings["keep_intermediate"]:
                    _LOGGER.debug(
                        "Deleting %d intermediate files", len(delete_folder_clips)
                    )
                    delete_intermediate(delete_folder_clips)
        else:
            delete_folder_files = False

        # Delete the source files if stated to delete.
        # We only do so if there were no issues in processing the clips
        if delete_folder_files:
            print(
                f"{get_current_timestamp()}\t\tDeleting {len(delete_file_list) + 2} "
                "files and folder {event_folder}"
            )
            delete_intermediate(delete_file_list)
            # Delete the metadata (event.json) and picture (thumb.png) files.
            delete_intermediate(
                [
                    os.path.join(event_folder, "event.json"),
                    os.path.join(event_folder, "thumb.png"),
                ]
            )

            # And delete the folder
            delete_intermediate([event_folder])

    # Now that we have gone through all the folders merge.
    # We only do this if merge is enabled OR if we only have 1 movie with 1 event clip
    # and for output a specific filename was provided not matching the filename for the
    # event clip
    movies_list: list[tuple[str | None, str]] | None = None
    if movies:
        first_item = list(movies.values())[0].first_item if len(movies) > 0 else None
        merge_subdirs: bool = video_settings["merge_subdirs"]
        if merge_subdirs or (
            video_settings["target_filename"] is not None
            and first_item is not None
            and first_item.filename is not None
            and first_item.filename
            != os.path.join(
                video_settings["target_folder"], video_settings["target_filename"]
            )
        ):
            movies_list = []
            merge_group_template = video_settings["merge_group_template"]
            if merge_group_template is not None or merge_group_template == "":
                _LOGGER.debug(
                    "Merging video files in groups based on template "
                    "%s, %d will be created.",
                    merge_group_template,
                    len(movies),
                )
            elif merge_subdirs:
                _LOGGER.debug(
                    "Merging video files into video file %s.",
                    video_settings["movie_filename"],
                )

            for movie in sorted(movies.keys()):
                if merge_group_template is not None and merge_group_template != "":
                    movie_filename = movie + ".mp4"
                else:
                    movie_filename = video_settings["movie_filename"]
                    # Make sure it ends in .mp4
                    if os.path.splitext(movie_filename)[1] != ".mp4":
                        movie_filename = movie_filename + ".mp4"

                # Add target folder to it
                movie_filename = os.path.join(
                    video_settings["target_folder"], movie_filename
                )
                print(
                    f"{get_current_timestamp()}\tCreating movie {movie_filename}, "
                    "please be patient."
                )

                # Only set title screen map if requested and # of events for this movie
                # is greater then 1
                title_screen_map: bool = (
                    video_settings["video_layout"].title_screen_map
                    and movies[movie].count > 1
                )

                if create_movie(
                    movies[movie],
                    movies[movie].items_sorted,
                    movie_filename,
                    video_settings,
                    video_settings["chapter_offset"],
                    title_screen_map,
                ):
                    if movies[movie].filename is not None:
                        movies_list.append(
                            (
                                movies[movie].filename,
                                str(
                                    timedelta(seconds=int(movies[movie].duration or 0))
                                ),
                            )
                        )

                        # Delete the 1 event movie if we created the movie because
                        # there was only 1 folder.
                        if (
                            not merge_subdirs
                            and first_item is not None
                            and first_item.filename is not None
                        ):
                            _LOGGER.debug(
                                "Deleting %d event file",
                                first_item.filename,
                            )
                            delete_intermediate([first_item.filename])
                        elif not video_settings["keep_events"]:
                            # Delete the event files now.
                            delete_file_list = []
                            for _, event_info in movies[movie].items:
                                if event_info.filename is not None:
                                    delete_file_list.append(event_info.filename)
                            _LOGGER.debug(
                                "Deleting %d event files", len(delete_file_list)
                            )
                            delete_intermediate(delete_file_list)
        else:
            print(
                f"{get_current_timestamp()}All folders have been processed, resulting "
                f"movie files are located in {video_settings['target_folder']}"
            )
    else:
        print(f"{get_current_timestamp()}No clips found.")

    end_time = timestamp()
    print(
        f"{get_current_timestamp()}Total processing time: "
        f"{str(timedelta(seconds=int((end_time - start_time))))}"
    )
    if video_settings["notification"]:
        if movies_list is None:
            # No merging of movies occurred.
            message = (
                "{total_folders} folder{folders} with {total_clips} clip{clips} have"
                "been processed, {target_folder} contains resulting files.".format(
                    folders="" if len(event_list) < 2 else "s",
                    total_folders=len(event_list),
                    clips="" if total_clips < 2 else "s",
                    total_clips=total_clips,
                    target_folder=video_settings["target_folder"],
                )
            )
        else:
            if len(movies_list) == 1:
                # Only 1 movie was created.
                print(
                    f"{get_current_timestamp()} Movie {movies_list[0][0]} with "
                    f"duration {movies_list[0][0]} has been created."
                )

            else:
                # Multiple movies were created, listing them all out.
                print(f"{get_current_timestamp()} Following movies have been created:")
                for movie_entry in movies_list:
                    print(
                        f"{get_current_timestamp()}\t{movie_entry[0]} with "
                        f"duration {movie_entry[1]}"
                    )

            if len(movies) == len(movies_list):
                # Number of movies created matches how many we should have created.
                message = (
                    "{total_folders} folder{folders} with {total_clips} clip{clips} "
                    "have been processed, {total_movies} movie {movies} been "
                    "created.".format(
                        folders="" if len(event_list) < 2 else "s",
                        total_folders=len(event_list),
                        clips="" if total_clips < 2 else "s",
                        total_clips=total_clips,
                        total_movies=len(movies_list),
                        movies="has" if len(movies_list) == 1 else "have",
                    )
                )
            else:
                # Seems creation of some movies failed.
                message = (
                    "{total_folders} folder{folders} with {total_clips} clip{clips} "
                    "have been processed, {total_movies} {movies} been created out of "
                    "{all_movies}.".format(
                        folders="" if len(event_list) < 2 else "s",
                        total_folders=len(event_list),
                        clips="" if total_clips < 2 else "s",
                        total_clips=total_clips,
                        total_movies=len(movies_list),
                        movies="has" if len(movies_list) == 1 else "have",
                        all_movies=len(movies),
                    )
                )

        notify("TeslaCam", "Completed", message)
        print(message)

    print()


def resource_path(relative_path):
    """Return absolute path for provided relative item based on location

    of program.
    """
    # If compiled with pyinstaller then sys._MEIPASS points to the location
    # of the bundle. Otherwise path of python script is used.
    base_path = getattr(sys, "_MEIPASS", str(Path(__file__).parent))
    return os.path.join(base_path, relative_path)


def notify_macos(title, subtitle, message):
    """Notification on MacOS"""
    try:
        run(
            [
                "osascript",
                f'-e display notification "{message}" with title "{title}" '
                f'subtitle "{subtitle}"',
            ],
            check=True,
        )
    except CalledProcessError as exc:
        _LOGGER.error("Failed in notifification: %s", exc)


def notify_windows(title, subtitle, message):
    """Notification on Windows"""

    try:
        toast(
            threaded=True,
            title=f"{title} {subtitle}",
            body=message,
            duration=5,
            icon=resource_path("tesla_dashcam.ico"),
        )
    except CalledProcessError as exc:
        _LOGGER.error("Failed in notifification: %s", exc)


def notify_linux(title, subtitle, message):
    """Notification on Linux"""
    try:
        run(["notify-send", f'"{title} {subtitle}"', f'"{message}"'], check=True)
    except CalledProcessError as exc:
        _LOGGER.error("Failed in notifification: %s", exc)


def notify(title, subtitle, message):
    """Call function to send notification based on OS"""
    if PLATFORM == "darwin":
        notify_macos(title, subtitle, message)
    elif PLATFORM == "win32":
        notify_windows(title, subtitle, message)
    elif PLATFORM == "linux":
        notify_linux(title, subtitle, message)


def main() -> int:
    """Main function"""

    loglevels = dict(
        (logging.getLevelName(level), level) for level in [10, 20, 30, 40, 50]
    )

    movie_folder = os.path.join(str(Path.home()), MOVIE_HOMEDIR.get(PLATFORM, ""), "")

    # Check if ffmpeg exist, if not then hope it is in default path or
    # provided.
    internal_ffmpeg = getattr(sys, "frozen", None) is not None
    ffmpeg_default = resource_path(FFMPEG.get(PLATFORM, "ffmpeg"))

    if not os.path.isfile(ffmpeg_default):
        internal_ffmpeg = False
        ffmpeg_default = FFMPEG.get(PLATFORM, "ffmpeg")

    epilog = (
        "This program leverages ffmpeg which is included. See https://ffmpeg.org/ for "
        "more information on ffmpeg"
        if internal_ffmpeg
        else "This program requires ffmpeg which can be downloaded from: "
        "https://ffmpeg.org/download.html"
    )

    parser = MyArgumentParser(
        description="tesla_dashcam - Tesla DashCam & Sentry Video Creator",
        epilog=epilog,
        formatter_class=SmartFormatter,
        fromfile_prefix_chars="@",
    )

    parser.add_argument(
        "source",
        type=str,
        nargs="*",
        help="Folder(s) (events) containing the saved camera files. Filenames can be "
        "provided as well to manage individual clips.",
    )

    parser.add_argument(
        "--version", action="version", version=" %(prog)s " + VERSION_STR
    )
    parser.add_argument(
        "--loglevel",
        default="INFO",
        choices=list(loglevels.keys()),
        type=str.upper,
        help="Logging level.",
    )
    parser.add_argument(
        "--ffmpeg_debug",
        action="store_true",
        help="Include output from ffmpeg when loglevel is set to debug.OUTPUT.",
    )
    parser.add_argument(
        "--temp_dir", required=False, type=str, help="R|Path to store temporary files."
    )
    parser.add_argument(
        "--no-notification",
        dest="system_notification",
        action="store_false",
        help="Do not create a notification upon completion.",
    )

    parser.add_argument(
        "--display_ts",
        action="store_true",
        help="Display timestamps on tesla_dashcam text output. DOES NOT AFFECT VIDEO "
        "OUTPUT.",
    )

    input_group = parser.add_argument_group(
        title="Video Input",
        description="Options related to what clips and events to process.",
    )
    input_group.add_argument(
        "--skip_existing",
        dest="skip_existing",
        action="store_true",
        help="Skip creating encoded video file if it already exist. Note that only "
        "existence is checked, not if layout etc. are the same.",
    )
    input_group.add_argument(
        "--delete_source",
        dest="delete_source",
        action="store_true",
        help="Delete the processed files upon completion.",
    )
    input_group.add_argument(
        "--exclude_subdirs",
        dest="exclude_subdirs",
        action="store_true",
        help="Do not search sub folders (events) for video files to process.",
    )

    monitor_group = parser.add_argument_group(
        title="Trigger Monitor",
        description="Parameters for monitoring of insertion of TeslaCam drive, folder, "
        "or file existence.",
    )
    monitor_group.add_argument(
        "--monitor",
        dest="monitor",
        action="store_true",
        help="Enable monitoring for drive to be attached with TeslaCam folder.",
    )
    monitor_group.add_argument(
        "--monitor_once",
        dest="monitor_once",
        action="store_true",
        help="Enable monitoring and exit once drive with TeslaCam folder has been "
        "attached and files processed.",
    )
    monitor_group.add_argument(
        "--monitor_trigger",
        required=False,
        type=str,
        help="Trigger file to look for instead of waiting for drive to be attached. "
        "Once file is discovered then processing will start, file will be deleted when "
        "processing has been completed. If source is not provided then folder where "
        "file is located will be used as source.",
    )

    layout_group = parser.add_argument_group(
        title="Video Layout",
        description="Set what the layout of the resulting video should be",
    )
    layout_group.add_argument(
        "--layout",
        required=False,
        choices=[
            "MOSAIC",
            "WIDESCREEN",
            "FULLSCREEN",
            "PERSPECTIVE",
            "CROSS",
            "DIAMOND",
            "HORIZONTAL",
        ],
        default="FULLSCREEN",
        type=str.upper,
        metavar="MOSAIC|FULLSCREEN|PERSPECTIVE|CROSS|DIAMOND|HORIZONTAL",
        help="R|Layout of the created video.\n"
        "    FULLSCREEN: Front camera center top with side and rear cameras smaller "
        "underneath it.\n"
        "    MOSAIC: Front and rear cameras on top with pillars and side cameras "
        "smaller underneath it.\n"
        "    PERSPECTIVE: Similar to FULLSCREEN but then with pillar and repeater "
        "cameras in perspective.\n"
        "    CROSS: Front camera center top, pillar cameras underneath, then side "
        "cameras underneath, and rear camera center bottom.\n"
        "    DIAMOND: Front camera center top, pillar cameras on left/right of front "
        "smaller, side cameras below on left/right of rear smaller, and rear camera "
        "center bottom.\n"
        "    HORIZONTAL: All cameras in horizontal line: left, left pillar, front, "
        "rear, right pillar, right.\n",
    )
    layout_group.add_argument(
        "--camera_position",
        dest="clip_pos",
        type=str.lower,
        nargs="+",
        action="append",
        help="R|Set camera clip position within video. Selecting this will override the"
        " layout selected!\n"
        "The camera clip scale will be set to 1280x960, use scale to adjust "
        "accordingly.\n"
        "Default layout is:\n"
        "    Front: 0x0\n"
        "    Rear: <front x-pos + width>x0\n"
        "    Left Pillar: 0x<max(front y-pos + height,rear y-pos + height)>\n"
        "    Right Pillar: <left pillar x-pos + width>x<max(front y-pos + height,rear "
        "ypos + height)>\n"
        "    Left: 0x<max(<left pillar y-pos + height>, <right pillar y-pos + height>\n"
        "    Right: <left-pillar x-pos + width>x<max(<left pillar y-pos + height>, "
        "<right pillar y-pos + height>\n"
        "Using this together with argument camera_order allows one to completely "
        "customize the layout\n"
        "Note that layout chosen also determines camera clip size and thus default "
        "position. See scale for respective sizing.\n"
        "Further, changing the scale of a camera clip would further impact potential "
        "positioning."
        "for example:\n"
        "  --camera_position camera=left 640x480                          Position "
        "left camera at 640x480\n"
        "  --camera_position camera=right x_pos=640                        Position "
        "right camera at x-position 640, y-position based on layout\n"
        "  --camera_position camera=front y_pos=480                        Position "
        "front camera at x-position based on layout, y-position at 480\n"
        "  --camera_position camera=rear  1280x960                        Position "
        "rear camera at 1280x960\n"
        "  --camera_position camera=left_pillar 0x960                     Position "
        "left pillar camera at 0x960\n",
    )

    layout_group.add_argument(
        "--camera_order",
        dest="clip_order",
        type=str.lower,
        help="R|Determines the order of processing the camera. Normally this is not "
        "required unless there is overlap.\n"
        "When using argument camera_position it is possible to overlap cameras "
        "partially or completely, by then\n"
        "leveraging this argument one can determine which camera will be on top and "
        "which one will be bottom."
        " Default order is: left, right, front, rear, left_pillar, right_pillar. If "
        "there is no overlap then the order does not matter.\n"
        " If not all cameras are specified then default order will be followed for "
        "those not specified, and thus be more on top."
        "for example:\n"
        "  --camera_order front,rear,left,right,left_pillar,right_pillar    Makes it "
        "that right_pillar will be on top, then left_pillar, then right, then left, "
        "then rear, and front at the bottom.\n",
    )
    layout_group.set_defaults(
        clip_order="front,rear,left,right,left_pillar,right_pillar"
    )

    layout_group.add_argument(
        "--perspective",
        dest="perspective",
        action="store_true",
        help="Show side cameras in perspective.",
    )
    layout_group.set_defaults(perspective=False)
    layout_group.add_argument(
        "--scale",
        dest="clip_scale",
        type=str.lower,
        nargs="+",
        action="append",
        help="R|Set camera clip scale for all clips, scale of 1 is 1280x960 camera "
        "clip.\n"
        "If provided with value then it is default for all cameras, to set the scale "
        "for a specific "
        "camera provide camera=<front, left, right, rear, left_pillar, right_pillar> "
        "<scale>\n"
        "for example:\n"
        "  --scale 0.5                                             all are 640x480\n"
        "  --scale 640x480                                         all are 640x480\n"
        "  --scale 0.5 --scale camera=front 1                      all are 640x480 "
        "except front at 1280x960\n"
        "  --scale camera=left .25 --scale camera=right 320x240    left and right are "
        "set to 320x240\n"
        "  --scale camera=left_pillar 0.25                         left pillar camera "
        "is set to 320x240\n"
        "Defaults:\n"
        "    MOSAIC: 1/2 (all cameras 640x480 base, front/rear boosted to 1216x912, "
        "video is 2496x1824)\n"
        "    FULLSCREEN: 1/2 (640x480, video is 1920x960)\n"
        "    CROSS: 1/2 (640x480, video is 1280x1920)\n"
        "    DIAMOND: 1/2 (640x480, video is 2560x1920)\n",
    )
    layout_group.add_argument(
        "--mirror",
        dest="rear_or_mirror",
        action="store_const",
        const=1,
        help="Video from side and rear cameras as if being viewed through the mirror. "
        "Default when not providing "
        "parameter --no-front. Cannot be used in combination with --rear.",
    )
    layout_group.add_argument(
        "--rear",
        dest="rear_or_mirror",
        action="store_const",
        const=0,
        help="Video from side and rear cameras as if looking backwards. Default when "
        "providing parameter --no-front. "
        "Cannot be used in combination with --mirror.",
    )
    layout_group.add_argument(
        "--swap",
        dest="swap_leftright",
        action="store_const",
        const=1,
        help="Swap left and right cameras in output, default when side and rear cameras"
        " are as if looking backwards. "
        "See --rear parameter.",
    )
    layout_group.add_argument(
        "--no-swap",
        dest="swap_leftright",
        action="store_const",
        const=0,
        help="Do not swap left and right cameras, default when side and rear cameras "
        "are as if looking through a "
        "mirror. Also see --mirror parameter",
    )
    layout_group.add_argument(
        "--swap_frontrear",
        dest="swap_frontrear",
        action="store_true",
        help="Swap front and rear cameras in output.",
    )

    layout_group.add_argument(
        "--swap_pillar",
        dest="swap_pillar",
        action="store_true",
        help="Swap left- and right pillar cameras in output.",
    )
    layout_group.add_argument(
        "--background",
        dest="background",
        default="black",
        type=str.lower,
        help="Background color for video. Can be a color string or RGB value. Also see "
        "--fontcolor.",
    )

    layout_group.add_argument(
        "--title_screen_map",
        dest="title_screen_map",
        action="store_true",
        help="Show a map of the event location for the first 3 seconds of the event "
        "movie, when merging events it will also create map with lines linking the "
        "events",
    )

    camera_group = parser.add_argument_group(
        title="Camera Exclusion", description="Exclude one or more cameras:"
    )
    camera_group.add_argument(
        "--no-front",
        dest="no_front",
        action="store_true",
        help="Exclude front camera from video.",
    )
    camera_group.add_argument(
        "--no-left",
        dest="no_left",
        action="store_true",
        help="Exclude left camera from video.",
    )
    camera_group.add_argument(
        "--no-right",
        dest="no_right",
        action="store_true",
        help="Exclude right camera from video.",
    )
    camera_group.add_argument(
        "--no-rear",
        dest="no_rear",
        action="store_true",
        help="Exclude rear camera from video.",
    )
    camera_group.add_argument(
        "--no-left-pillar",
        dest="no_left_pillar",
        action="store_true",
        help="Exclude left pillar camera from video.",
    )
    camera_group.add_argument(
        "--no-right-pillar",
        dest="no_right_pillar",
        action="store_true",
        help="Exclude right pillar camera from video.",
    )

    text_overlay_group = parser.add_argument_group(
        title="Text Overlay",
        description="Options on how to show text in resulting video:",
    )
    text_overlay_group.add_argument(
        "--no-timestamp",
        dest="no_timestamp",
        action="store_true",
        help="Do not show timestamp in video",
    )
    text_overlay_group.add_argument(
        "--halign",
        required=False,
        choices=["LEFT", "CENTER", "RIGHT"],
        type=str.upper,
        help="Horizontal alignment for timestamp",
    )
    text_overlay_group.add_argument(
        "--valign",
        required=False,
        choices=["TOP", "MIDDLE", "BOTTOM"],
        type=str.upper,
        help="Vertical Alignment for timestamp",
    )
    text_overlay_group.add_argument(
        "--font",
        required=False,
        type=str,
        default=DEFAULT_FONT.get(PLATFORM, None),
        help="Fully qualified filename (.ttf) to the font to be chosen for timestamp.",
    )
    text_overlay_group.add_argument(
        "--fontsize",
        required=False,
        type=int,
        help="Font size for timestamp. Default is scaled based on resulting video "
        "size.",
    )
    text_overlay_group.add_argument(
        "--fontcolor",
        required=False,
        type=str.lower,
        default="white",
        help="R|Font color for timestamp. Any color is accepted as a color string or "
        "RGB value.\n"
        "Some potential values are:\n"
        "    white\n"
        "    yellowgreen\n"
        "    yellowgreen@0.9\n"
        "    Red\n:"
        "    0x2E8B57\n"
        "For more information on this see ffmpeg documentation for color: "
        "https://ffmpeg.org/ffmpeg-utils.html#Color",
    )
    text_overlay_group.add_argument(
        "--text_overlay_fmt",
        required=False,
        type=str,
        default="{local_timestamp_rolling}",
        help="R|Format string for text overlay.\n"
        "Valid format variables:\n"
        "    {clip_start_timestamp} - Local time the clip starts at\n"
        "    {clip_end_timestamp} - Local time the clip ends at\n"
        "    {local_timestamp_rolling} - Local time which continuously updates "
        "(shorthand for '%%{{pts:localtime:{local_timestamp}:%%x %%X}}'), string\n"
        "    {event_timestamp} - Timestamp from events.json (if provided), string\n"
        "    {event_timestamp_countdown_rolling} - Local time which continuously "
        "updates (shorthand for '%%{{hms:localtime:{event_timestamp}}}'), string\n"
        "    {event_city} - City name from events.json (if provided), string\n"
        "    {event_street} - Street name from events.json (if provided), string\n"
        "    {event_reason} - Recording reason from events.json (if provided), string\n"
        "    {event_latitude} - Estimated latitude from events.json (if provided), "
        "float\n"
        "    {event_longitude} - Estimated longitude from events.json (if provided), "
        "float\n"
        "    \n"
        "    All valid ffmpeg 'text expansion' syntax is accepted here.\n"
        "    More info: http://ffmpeg.org/ffmpeg-filters.html#Text-expansion\n",
    )
    text_overlay_group.add_argument(
        "--timestamp_format",
        required=False,
        type=str,
        default="%x %X",
        help="R|Format for timestamps.\n "
        "Determines how timestamps should be represented. Any valid value from strftime"
        " is accepted."
        "Default is set '%%x %%X' which is locale's appropriate date and time "
        "representation"
        "More info: https://strftime.org",
    )

    filter_group = parser.add_argument_group(
        title="Timestamp Restriction",
        description="Restrict video to be between start and/or end timestamps. "
        "Timestamp to be provided in a ISO-8601 "
        "format (see https://fits.gsfc.nasa.gov/iso-time.html for examples)",
    )
    filter_group.add_argument(
        "--start_timestamp", dest="start_timestamp", type=str, help="Starting timestamp"
    )
    filter_group.add_argument(
        "--end_timestamp",
        dest="end_timestamp",
        type=str,
        # type=lambda d: datetime.strptime(d, "%Y-%m-%d_%H-%M-%S").datetime(),
        help="Ending timestamp",
    )

    offset_group = parser.add_argument_group(
        title="Event offsets", description="Start and/or end offsets for events"
    )
    offset_group.add_argument(
        "--start_offset",
        dest="start_offset",
        type=int,
        help="Set starting time for resulting video. Default is 0 seconds, 60 seconds "
        "if --sentry_offset is provided.",
    )
    offset_group.add_argument(
        "--end_offset",
        dest="end_offset",
        type=int,
        help="Set ending time for resulting video. Default is 0 seconds, 30 seconds if"
        " --sentry_offset is provided.",
    )

    offset_group.add_argument(
        "--sentry_offset",
        dest="sentry_offset",
        action="store_true",
        help="R|start_offset and end_offset will be based on when timestamp of object "
        "detection occurred for Sentry"
        "events instead of start/end of event.\n"
        "Ignored if either --sentry_start_offset or --senty_end_offset are provided.\n"
        "Note, legacy option that will be removed in future.",
    )

    offset_group.add_argument(
        "--sentry_start_offset",
        dest="sentry_start_offset",
        type=int,
        help="Set starting time for resulting video. Default is 0 seconds, 60 seconds "
        "if --sentry_offset is provided.",
    )
    offset_group.add_argument(
        "--sentry_end_offset",
        dest="sentry_end_offset",
        type=int,
        help="Set ending time for resulting video. Default is 0 seconds, 30 seconds "
        "if --sentry_offset is provided.",
    )

    output_group = parser.add_argument_group(
        title="Video Output", description="Options related to resulting video creation."
    )
    output_group.add_argument(
        "--output",
        required=False,
        default=movie_folder,
        type=str,
        help="R|Path/Filename for the new movie file. Event files will be stored in "
        "same folder." + os.linesep,
    )
    output_group.add_argument(
        "--motion_only",
        dest="motion_only",
        action="store_true",
        help="Fast-forward through video when there is no motion.",
    )
    output_group.add_argument(
        "--slowdown",
        dest="slow_down",
        type=float,
        default=argparse.SUPPRESS,
        help="Slow down video output. Accepts a number that is then used as multiplier,"
        " providing 2 means half the speed.",
    )
    output_group.add_argument(
        "--speedup",
        dest="speed_up",
        type=float,
        default=argparse.SUPPRESS,
        help="Speed up the video. Accepts a number that is then used as a multiplier, "
        "providing 2 means "
        "twice the speed.",
    )
    output_group.add_argument(
        "--chapter_offset",
        dest="chapter_offset",
        type=int,
        default=0,
        help="Offset in seconds for chapters in merged video. Negative offset is # of "
        "seconds before the end of the "
        "subdir video, positive offset if # of seconds after the start of the subdir "
        "video.",
    )

    output_group.add_argument(
        "--merge",
        required=False,
        dest="merge_group_template",
        type=str,
        nargs="?",
        const="",
        default=argparse.SUPPRESS,
        help="R|Merge the video files from different folders (events) into 1 big video "
        "file.\n"
        "Optionally add a template string to group events in different video files "
        "based on the template.\n"
        "Valid format variables:\n"
        "    {layout} - Layout of the created movie (see --layout)\n"
        "    {start_timestamp} - Local time the event started at\n"
        "    {end_timestamp} - Local time the event ends at\n"
        "    {event_timestamp} - Timestamp from events.json (if provided), string\n"
        "    {event_city} - City name from events.json (if provided), string\n"
        "    {event_street} - Street name from events.json (if provided), string\n"
        "    {event_reason} - Recording reason from events.json (if provided), string\n"
        "    {event_latitude} - Latitude from events.json (if provided), float\n"
        "    {event_longitude} - Longitude from events.json (if provided), float\n",
    )

    output_group.add_argument(
        "--merge_timestamp_format",
        required=False,
        type=str,
        default="%Y-%m-%d_%H_%M",
        help="R|Format for timestamps in merge_template.\n "
        "Determines how timestamps should be represented within merge_template. Any "
        "valid value from strftime is accepted."
        "Default is set '%%Y-%%m-%%d_%%H_%%M'"
        "More info: https://strftime.org",
    )

    output_group.add_argument(
        "--keep-intermediate",
        dest="keep_intermediate",
        action="store_true",
        help="Do not remove the clip video files that are created",
    )

    output_group.add_argument(
        "--keep-events",
        dest="keep_events",
        action="store_true",
        help="Do not remove the event video files that are created when merging events "
        "into a video file (see --merge)",
    )

    output_group.add_argument(
        "--set_moviefile_timestamp",
        dest="set_moviefile_timestamp",
        required=False,
        choices=["START", "STOP", "SENTRY", "RENDER"],
        type=str.upper,
        default="START",
        help="Match modification timestamp of resulting video files to event timestamp."
        " Use START to match with when the event started, STOP for end time of the "
        "event, SENTRY for Sentry event timestamp, or RENDER to not change it.",
    )

    advancedencoding_group = parser.add_argument_group(
        title="Advanced encoding settings", description="Advanced options for encoding"
    )

    if PLATFORM == "darwin":
        nogpuhelp = (
            "R|Disable use of GPU acceleration, default is to use GPU acceleration.\n"
        )
        gpuhelp = "R|Use GPU acceleration (this is the default).\n"

        advancedencoding_group.add_argument(
            "--no-gpu",
            dest="gpu",
            action="store_false",
            default=argparse.SUPPRESS,
            help=nogpuhelp,
        )

        advancedencoding_group.add_argument(
            "--gpu",
            dest="gpu",
            action="store_true",
            default=argparse.SUPPRESS,
            help=gpuhelp,
        )

    elif PLATFORM != "darwin":
        advancedencoding_group.add_argument(
            "--no-gpu",
            dest="gpu",
            action="store_false",
            default=argparse.SUPPRESS,
            help="R|Disable use of GPU acceleration, this is the default.\n",
        )

        advancedencoding_group.add_argument(
            "--gpu",
            dest="gpu",
            action="store_true",
            default=argparse.SUPPRESS,
            help="R|Use GPU acceleration, only enable if supported by hardware.\n"
            " --gpu_type has to be provided as well when enabling this parameter",
        )

        advancedencoding_group.add_argument(
            "--gpu_type",
            choices=["nvidia", "intel", "qsv", "rpi", "vaapi"]
            if PLATFORM == "linux"
            else ["nvidia", "intel", "vaapi"],
            type=str.lower,
            help="Type of graphics card (GPU) in the system. This determines the "
            "encoder that will be used."
            "This parameter is mandatory if --gpu is provided.",
        )

    advancedencoding_group.add_argument(
        "--no-faststart",
        dest="faststart",
        action="store_true",
        help="Do not enable flag faststart on the resulting video files. Use this when "
        "using a network share and "
        "errors occur during encoding.",
    )

    advancedencoding_group.add_argument(
        "--quality",
        required=False,
        choices=["LOWEST", "LOWER", "LOW", "MEDIUM", "HIGH"],
        default="LOWER",
        type=str.upper,
        help="Define the quality setting for the video, higher quality means bigger "
        "file size but might "
        "not be noticeable.",
    )

    advancedencoding_group.add_argument(
        "--compression",
        required=False,
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
        default="medium",
        type=str.lower,
        help="Speed to optimize video. Faster speed results in a bigger file. This "
        "does not impact the quality of the video, just how much time is used to "
        "compress it.",
    )

    advancedencoding_group.add_argument(
        "--fps",
        required=False,
        type=int,
        default=24,
        help="Frames per second for resulting video. Tesla records at about 33fps "
        "hence going higher wouldn't do much as frames would just be duplicated. "
        "Default is 24fps which is the standard for movies and TV shows",
    )

    if internal_ffmpeg:
        advancedencoding_group.add_argument(
            "--ffmpeg",
            required=False,
            type=str,
            default=argparse.SUPPRESS,
            help="Full path and filename for alternative ffmpeg.",
        )
    else:
        advancedencoding_group.add_argument(
            "--ffmpeg",
            required=False,
            type=str,
            default=ffmpeg_default,
            help="Path and filename for ffmpeg. Specify if ffmpeg is not within path.",
        )

    advancedencoding_group.add_argument(
        "--encoding",
        required=False,
        choices=["x264", "x265"],
        type=str.lower,
        default=argparse.SUPPRESS,
        help="R|Encoding to use for video creation.\n"
        "    x264: standard encoding, can be viewed on most devices but results in "
        "bigger file.\n"
        "    x265: newer encoding standard but not all devices support this yet.\n",
    )
    advancedencoding_group.add_argument(
        "--enc",
        required=False,
        type=str,
        default=argparse.SUPPRESS,
        help="R|Provide a custom encoder for video creation. Cannot be used in "
        "combination with --encoding.\n"
        "Note: when using this option the --gpu option is ignored. To use GPU hardware "
        "acceleration specify an encoding that provides this.",
    )

    update_check_group = parser.add_argument_group(
        title="Update Check", description="Check for updates"
    )
    update_check_group.add_argument(
        "--check_for_update",
        dest="check_for_updates",
        action="store_true",
        help="Check for update and exit.",
    )
    update_check_group.add_argument(
        "--no-check_for_update",
        dest="no_check_for_updates",
        action="store_true",
        help="A check for new updates is performed every time. With this parameter that"
        " can be disabled",
    )
    update_check_group.add_argument(
        "--include_test",
        dest="include_beta",
        action="store_true",
        help="Include test (beta) releases when checking for updates.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=loglevels[args.loglevel],
        format="%(asctime)s:%(levelname)s:\t%(name)s\t%(message)s",
    )

    if args.ffmpeg_debug:
        global FFMPEG_DEBUG  # pylint: disable=global-statement
        FFMPEG_DEBUG = True

    _LOGGER.debug("Arguments : %s", args)
    _LOGGER.debug("Platform is %s", PLATFORM)
    _LOGGER.debug("Processor is %s", PROCESSOR)

    # Check that any mutual exclusive items are not both provided.
    if "speed_up" in args and "slow_down" in args:
        print(
            f"{get_current_timestamp()}Option --speed_up and option --slow_down cannot "
            "be used together, only use one of them."
        )
        return 1

    if "enc" in args and "encoding" in args:
        print(
            f"{get_current_timestamp()}Option --enc and option --encoding cannot be "
            "used together, only use one of them."
        )
        return 1

    if not args.no_check_for_updates or args.check_for_updates:
        release_info = check_latest_release(args.include_beta)
        if release_info is not None:
            new_version = False
            if release_info.get("tag_name") is not None:
                github_version = release_info.get("tag_name", "").split(".")
                if len(github_version) == 3:
                    # Release tags normally start with v. If that is the case
                    # then strip the v.
                    try:
                        major_version = int(github_version[0])
                    except ValueError:
                        major_version = int(github_version[0][1:])

                    minor_version = int(github_version[1])
                    if release_info.get("prerelease"):
                        # Drafts will have b and then beta number.
                        patch_version = int(github_version[2].split("b")[0])
                        beta_version = int(github_version[2].split("b")[1])
                    else:
                        patch_version = int(github_version[2])
                        beta_version = -1

                    if major_version == VERSION["major"]:
                        if minor_version == VERSION["minor"]:
                            if patch_version == VERSION["patch"]:
                                if beta_version > VERSION["beta"] or (
                                    beta_version == -1 and VERSION["beta"] != -1
                                ):
                                    new_version = True
                            elif patch_version > VERSION["patch"]:
                                new_version = True
                        elif minor_version > VERSION["minor"]:
                            new_version = True
                    elif major_version > VERSION["major"]:
                        new_version = True

            if new_version:
                beta = ""
                if release_info.get("prerelease"):
                    beta = "beta "

                release_notes = ""
                if not args.check_for_updates:
                    if args.system_notification:
                        notify(
                            "TeslaCam",
                            "Update available",
                            f"New {beta}release {release_info.get('tag_name')} is "
                            f"available. You are on version {VERSION_STR}",
                        )
                    release_notes = (
                        "Use --check_for_update to get latest release notes."
                    )

                print(
                    f"{get_current_timestamp()}New {beta}release "
                    f"{release_info.get('tag_name')} is available for download "
                    f"({release_info.get('html_url')}). You are currently on "
                    f"{VERSION_STR}. {release_notes}"
                )

                if args.check_for_updates:
                    print(
                        f"{get_current_timestamp()}You can download the new release "
                        f"from: {release_info.get('html_url')}"
                    )
                    print(
                        f"{get_current_timestamp()}Release Notes:\n "
                        f"{release_info.get('body')}"
                    )
                    return 0
            else:
                if args.check_for_updates:
                    print(
                        f"{get_current_timestamp()}{VERSION_STR} is the latest release "
                        "available."
                    )
                    return 0
        else:
            print(f"{get_current_timestamp()} Did not retrieve latest version info.")

    internal_ffmpeg = getattr(args, "ffmpeg", None) is None and internal_ffmpeg
    ffmpeg = getattr(args, "ffmpeg", ffmpeg_default) or ""
    if not internal_ffmpeg and (ffmpeg == "" or which(ffmpeg) is None):
        print(
            f"{get_current_timestamp()}ffmpeg is a requirement, unable to find {ffmpeg}"
            " executable. Please ensure it exist and is located within PATH "
            "environment or provide full path using parameter --ffmpeg."
        )
        return 1

    if internal_ffmpeg and PLATFORM == "darwin" and PROCESSOR == "arm":
        print(
            "Internal ffmpeg version is used which has been compiled for Intel Macs. "
            "Better results in both performance and size can be achieved by downloading"
            " an Apple Silicon compiled ffmpeg from: https://www.osxexperts.net and "
            "providing it leveraging the --ffmpeg parameter."
        )

    if args.clip_pos:
        # If clip positions have been provided it is custom.
        layout_settings = MovieLayout()
    elif args.layout == "PERSPECTIVE":
        layout_settings = FullScreen()
        layout_settings.perspective = True
    else:
        # Map legacy WIDESCREEN to MOSAIC
        layout_name = "MOSAIC" if args.layout == "WIDESCREEN" else args.layout
        if layout_name == "MOSAIC":
            layout_settings = Mosaic()
        elif layout_name == "FULLSCREEN":
            layout_settings = FullScreen()
        elif layout_name == "CROSS":
            layout_settings = Cross()
        elif layout_name == "DIAMOND":
            layout_settings = Diamond()
        elif layout_name == "HORIZONTAL":
            layout_settings = Horizontal()
        else:
            layout_settings = FullScreen()

        layout_settings.perspective = args.perspective

    # Determine if left and right cameras should be swapped or not.
    # No more arguments related to cameras (i.e .scale, include or not) can be
    # processed from now on.
    # Up till now left means left camera and right means right camera.
    # From this point forward left can mean right camera if we're swapping output.
    layout_settings.swap_front_rear = args.swap_frontrear

    if layout_settings.swap_front_rear:
        layout_settings.cameras("front").include = not args.no_rear
        layout_settings.cameras("rear").include = not args.no_front
    else:
        layout_settings.cameras("front").include = not args.no_front
        layout_settings.cameras("rear").include = not args.no_rear

    # Check if either rear or mirror argument has been provided.
    # If front camera then default to mirror, if no front camera then default to rear.
    side_camera_as_mirror = (
        not args.no_front if args.rear_or_mirror is None else args.rear_or_mirror
    )
    layout_settings.cameras("left").mirror = side_camera_as_mirror
    layout_settings.cameras("right").mirror = side_camera_as_mirror
    layout_settings.cameras("front").mirror = (
        layout_settings.cameras("left").mirror
        if layout_settings.swap_front_rear
        else False
    )
    layout_settings.cameras("front").mirror = (
        True if layout_settings.swap_front_rear and side_camera_as_mirror else False
    )
    layout_settings.cameras("rear").mirror = (
        True if not layout_settings.swap_front_rear and side_camera_as_mirror else False
    )

    layout_settings.swap_left_right = (
        not side_camera_as_mirror
        if args.swap_leftright is None
        else args.swap_leftright
    )

    if layout_settings.swap_left_right:
        layout_settings.cameras("left").include = not args.no_right
        layout_settings.cameras("right").include = not args.no_left
    else:
        layout_settings.cameras("left").include = not args.no_left
        layout_settings.cameras("right").include = not args.no_right

    layout_settings.swap_pillar = args.swap_pillar

    if layout_settings.swap_pillar:
        layout_settings.cameras("left_pillar").include = not args.no_right_pillar
        layout_settings.cameras("right_pillar").include = not args.no_left_pillar
    else:
        layout_settings.cameras("left_pillar").include = not args.no_left_pillar
        layout_settings.cameras("right_pillar").include = not args.no_right_pillar

    # For scale first set the main clip one if provided, this than allows camera
    # specific ones to override for that camera.
    scaling = parser.args_to_dict(args.clip_scale, "scale")
    main_scale = search_dict("camera", scaling, None)

    if main_scale is not None:
        layout_settings.scale = main_scale.get("scale", layout_settings.scale)

    for scale in scaling:
        camera = scale.get("camera", "").lower()
        if camera in ["front", "left", "right", "rear", "left_pillar", "right_pillar"]:
            if camera_scale := scale.get("scale"):
                layout_settings.cameras(camera).scale = camera_scale

    for pos in parser.args_to_dict(args.clip_pos, "x_y_pos"):
        camera = pos.get("camera", "").lower()
        if camera in ["front", "left", "right", "rear", "left_pillar", "right_pillar"]:
            x_pos, y_pos = None, None
            if x_y_pos := pos.get("x_y_pos"):
                x_y_pos = x_y_pos.split("x")
                x_pos = x_y_pos[0]
                if len(x_y_pos) == 2:
                    y_pos = x_y_pos[1]

            x_pos = pos.get("x_pos", x_pos)
            y_pos = pos.get("y_pos", y_pos)

            if x_pos is not None and x_pos.isnumeric():
                layout_settings.cameras(camera).xpos = x_pos

            if y_pos is not None and y_pos.isnumeric():
                layout_settings.cameras(camera).ypos = y_pos

    layout_settings.clip_order = args.clip_order.split(",")

    if args.halign is not None:
        layout_settings.font.halign = args.halign

    if args.valign is not None:
        layout_settings.font.valign = args.valign

    layout_settings.title_screen_map = args.title_screen_map

    layout_settings.background_color = args.background
    layout_settings.font.font = args.font
    layout_settings.font.color = args.fontcolor
    if args.fontsize is not None and args.fontsize > 0:
        layout_settings.font.size = args.fontsize

    # Text Overlay
    text_overlay_format = (
        args.text_overlay_fmt if args.text_overlay_fmt is not None else None
    )

    # Timestamp format
    timestamp_format = (
        args.timestamp_format if args.timestamp_format is not None else None
    )

    filter_counter = 0
    # input_clip is going to be last identifier set for cameras and positions and is
    # dynamic during processing.
    # Thus setting it like this here so that later it is replaced with the actual
    # input clip.
    input_clip = "{input_clip}"
    filter_string = ";[{input_clip}] {filter} [tmp{filter_counter}]"
    ffmpeg_timestamp = ""
    if not args.no_timestamp and text_overlay_format is not None:
        if layout_settings.font.font is None:
            print(
                f"{get_current_timestamp()}Unable to get a font file for platform "
                f"{PLATFORM}. Please provide valid font file using --font or disable "
                "timestamp using --no-timestamp."
            )
            return 0

        temp_font_file = (
            rf"c:\{layout_settings.font.font}"
            if PLATFORM == "win32"
            else layout_settings.font.font
        )
        if temp_font_file is None or temp_font_file == "":
            print(
                f"{get_current_timestamp()}Font file is not set for platform "
                f"{PLATFORM}. Please provide valid font file using --font."
            )
            return 0

        # Check if the font file exists.
        # If it does not exist then we cannot use it.
        # If it does not exist then we can also not use the timestamp.
        if not os.path.isfile(temp_font_file):
            print(
                f"{get_current_timestamp()}Font file {temp_font_file} does not exist. "
                "Provide a valid font file using --font or disable timestamp using "
                "--no-timestamp"
            )
            if PLATFORM == "linux":
                print(
                    f"{get_current_timestamp()}You can also install the fonts using for"
                    " example: apt-get install ttf-freefont"
                )
            return 0

        ffmpeg_timestamp = (
            ffmpeg_timestamp + f"drawtext=fontfile={layout_settings.font.font}:"
            f"fontcolor={layout_settings.font.color}:"
            f"fontsize={layout_settings.font.size}:borderw=2:bordercolor=black@1.0:"
            f"x={layout_settings.font.halign}:y={layout_settings.font.valign}:"
            "text='__USERTEXT__'"
        )

        ffmpeg_timestamp = filter_string.format(
            input_clip=input_clip,
            filter=ffmpeg_timestamp,
            filter_counter=filter_counter,
        )
        input_clip = f"tmp{filter_counter}"
        filter_counter += 1

    speed = args.slow_down if "slow_down" in args else ""
    speed = round(1 / args.speed_up, 4) if "speed_up" in args else speed
    ffmpeg_speed = ""
    if speed != "":
        ffmpeg_speed = filter_string.format(
            input_clip=input_clip,
            filter=f"setpts={speed}*PTS",
            filter_counter=filter_counter,
        )
        input_clip = f"tmp{filter_counter}"
        filter_counter += 1

    ffmpeg_motiononly = ""
    if args.motion_only:
        ffmpeg_motiononly = filter_string.format(
            input_clip=input_clip,
            filter="mpdecimate=hi=64*48, setpts=N/FRAME_RATE/TB, format=yuv420p",
            filter_counter=filter_counter,
        )
    else:
        ffmpeg_motiononly = filter_string.format(
            input_clip=input_clip,
            filter="format=yuv420p",
            filter_counter=filter_counter,
        )
    input_clip = f"tmp{filter_counter}"
    filter_counter += 1

    ffmpeg_params = ["-preset", args.compression, "-crf", MOVIE_QUALITY[args.quality]]

    use_gpu = (
        getattr(args, "gpu", True)
        if PLATFORM == "darwin"
        else getattr(args, "gpu", False)
    )

    video_encoding: list[str] = []
    ffmpeg_hwdev: list[str] = []
    ffmpeg_hwout: list[str] = []
    ffmpeg_hwupload: str = ""
    if "enc" not in args:
        encoding = args.encoding if "encoding" in args else "x264"

        # For x265 add QuickTime compatibility
        if encoding == "x265":
            video_encoding = video_encoding + ["-vtag", "hvc1"]

        # GPU acceleration enabled
        if use_gpu:
            if PLATFORM == "darwin":
                print(f"{get_current_timestamp()}GPU acceleration is enabled")
                video_encoding = video_encoding + ["-allow_sw", "1"]
                encoding = encoding + "_mac"

            else:
                if args.gpu_type is None:
                    print(
                        f"{get_current_timestamp()}Parameter --gpu_type is mandatory "
                        "when parameter --use_gpu is used."
                    )
                    return 0

                # Confirm that GPU acceleration with this encoding is supported.
                if MOVIE_ENCODING.get(encoding + "_" + args.gpu_type) is None:
                    # It is not, defaulting then to no GPU
                    print(
                        f"{get_current_timestamp()}GPU acceleration not available for "
                        f"encoding {encoding} and GPU type {args.gpu_type}. GPU "
                        "acceleration disabled."
                    )
                else:
                    print(f"{get_current_timestamp()}GPU acceleration is enabled.")
                    encoding = encoding + "_" + args.gpu_type

                    # If using vaapi hw acceleration this takes the decoding and filter
                    # processing done in softwareand passes it up to the GPU for
                    # hw accelerated encoding.
                    if args.gpu_type == "vaapi":
                        ffmpeg_hwupload = filter_string.format(
                            input_clip=input_clip,
                            filter="format=nv12,hwupload",
                            filter_counter=filter_counter,
                        )
                        input_clip = f"tmp{filter_counter}"
                        filter_counter += 1

                        if PLATFORM == "linux":
                            ffmpeg_hwdev = ffmpeg_hwdev + [
                                "-vaapi_device",
                                "/dev/dri/renderD128",
                            ]
                            ffmpeg_hwout = ffmpeg_hwout + [
                                "-hwaccel_output_format",
                                "vaapi",
                            ]
                    elif args.gpu_type == "qsv":
                        if PLATFORM == "linux":
                            ffmpeg_hwdev = ffmpeg_hwdev + [
                                "-qsv_device",
                                "/dev/dri/renderD128",
                            ]
                            ffmpeg_hwout = ffmpeg_hwout + ["-hwaccel", "qsv"]

            bit_rate = str(int(10000 * layout_settings.scale)) + "K"
            video_encoding = video_encoding + ["-b:v", bit_rate]

        video_encoding = video_encoding + ["-c:v", MOVIE_ENCODING[encoding]]
    else:
        video_encoding = video_encoding + ["-c:v", args.enc]

    ffmpeg_params = ffmpeg_params + video_encoding

    # Determine the target folder and filename.
    # If no extension then assume it is a folder.
    if (
        os.path.splitext(args.output)[1] is not None
        and os.path.splitext(args.output)[1] != ""
    ):
        target_folder, target_filename = os.path.split(args.output)
        if target_folder is None or target_folder == "":
            # If nothing in target_filename then no folder was given,
            # setting default movie folder
            target_folder = movie_folder
            target_filename = args.output
    else:
        # Folder only provided.
        target_folder = args.output
        target_filename = None

    # Convert target folder to absolute path if relative path has been provided.
    target_folder = os.path.abspath(
        os.path.expanduser(os.path.expandvars(target_folder))
    )

    # Ensure folder if not already exist and if not can be created
    if not make_folder("--output", target_folder):
        return 0

    temp_folder = args.temp_dir
    if temp_folder is not None:
        # Convert temp folder to absolute path if relative path has been provided
        temp_folder = os.path.abspath(
            os.path.expanduser(os.path.expandvars(args.temp_dir))
        )

        if not make_folder("--temp_dir", temp_folder):
            return 0

    # Set the run type based on arguments.
    runtype = "RUN"
    if args.monitor:
        runtype = "MONITOR"
    elif args.monitor_once:
        runtype = "MONITOR_ONCE"
    monitor_file = args.monitor_trigger

    # Set the display timestamp boolean.
    if args.display_ts:
        global DISPLAY_TS  # pylint: disable=global-statement
        DISPLAY_TS = True

    # If no source provided then set to MONITOR_ONCE and we're only going to
    # take SavedClips and SentryClips
    source_list = args.source
    if not source_list:
        source_list = ["SavedClips", "SentryClips"]
        if runtype == "RUN":
            runtype = "MONITOR_ONCE"

    start_timestamp = None
    if args.start_timestamp is not None:
        try:
            start_timestamp = isoparse(args.start_timestamp)
            _LOGGER.debug(
                f"Parsed start_timestamp: {start_timestamp}, tzinfo: {start_timestamp.tzinfo}"
            )
            if start_timestamp.tzinfo is None:
                start_timestamp = start_timestamp.astimezone(get_localzone())
                _LOGGER.debug(f"After local timezone conversion: {start_timestamp}")
            # Normalize to UTC for internal comparisons
            start_timestamp = start_timestamp.astimezone(timezone.utc)
            _LOGGER.debug(f"After UTC conversion: {start_timestamp}")
        except ValueError as e:
            print(
                f"{get_current_timestamp()}Start timestamp ({args.start_timestamp}) "
                "provided is in an incorrect "
                f"format. Parsing error: {str(e)}."
            )
            return 1

    end_timestamp = None
    if args.end_timestamp is not None:
        try:
            end_timestamp = isoparse(args.end_timestamp)
            _LOGGER.debug(
                f"Parsed end_timestamp: {end_timestamp}, tzinfo: {end_timestamp.tzinfo}"
            )
            if end_timestamp.tzinfo is None:
                end_timestamp = end_timestamp.astimezone(get_localzone())
                _LOGGER.debug(f"After local timezone conversion: {end_timestamp}")
            # Normalize to UTC for internal comparisons
            end_timestamp = end_timestamp.astimezone(timezone.utc)
            _LOGGER.debug(f"After UTC conversion: {end_timestamp}")
        except ValueError as e:
            print(
                f"{get_current_timestamp()}End timestamp ({args.end_timestamp}) "
                f"provided is in an incorrect format. Parsing error: {str(e)}."
            )
            return 1

    video_settings = {
        "source_folder": source_list,
        "exclude_subdirs": args.exclude_subdirs,
        "output": args.output,
        "target_folder": target_folder,
        "target_filename": target_filename,
        "temp_dir": temp_folder,
        "run_type": runtype,
        "merge_subdirs": True if "merge_group_template" in args else False,
        "merge_group_template": args.merge_group_template
        if "merge_group_template" in args
        else None,
        "merge_timestamp_format": args.merge_timestamp_format,
        "chapter_offset": args.chapter_offset,
        "movie_filename": None,
        "set_moviefile_timestamp": args.set_moviefile_timestamp,
        "keep_intermediate": args.keep_intermediate,
        "keep_events": args.keep_events,
        "notification": args.system_notification,
        "movie_layout": args.layout,
        "movie_speed": speed,
        "video_encoding": video_encoding,
        "movie_encoding": args.encoding if "encoding" in args else "x264",
        "fps": args.fps,
        "movie_compression": args.compression,
        "movie_quality": args.quality,
        "ffmpeg_exec": ffmpeg,
        "ffmpeg_hwdev": ffmpeg_hwdev,
        "ffmpeg_hwout": ffmpeg_hwout,
        "video_layout": layout_settings,
        "ffmpeg_text_overlay": ffmpeg_timestamp,
        "text_overlay_format": text_overlay_format,
        "timestamp_format": timestamp_format,
        "ffmpeg_speed": ffmpeg_speed,
        "ffmpeg_motiononly": ffmpeg_motiononly,
        "ffmpeg_hwupload": ffmpeg_hwupload,
        "movflags_faststart": not args.faststart,
        "input_clip": input_clip,
        "other_params": ffmpeg_params,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "start_offset": getattr(args, "start_offset", None),
        "end_offset": getattr(args, "end_offset", None),
        "sentry_start_offset": getattr(args, "sentry_start_offset", None),
        "sentry_end_offset": getattr(args, "sentry_end_offset", None),
        "sentry_offset": args.sentry_offset,
        "skip_existing": args.skip_existing,
    }

    # Confirm the merge variables provided are accurate.
    dummy_event = Event(folder="dummy")
    if (
        dummy_event.template(
            video_settings["merge_group_template"],
            video_settings["merge_timestamp_format"],
            video_settings,
        )
        is None
    ):
        # Invalid merge template provided, exiting.
        return 1

    replacement_strings = {
        "start_timestamp": "start_timestamp",
        "end_timestamp": "end_timestamp",
        "local_timestamp_rolling": "local_timestamp_rolling",
        "event_timestamp_countdown": "event_timestamp_countdown",
        "event_timestamp_countdown_rolling": "event_timestamp_countdown_rolling",
        "event_timestamp": "event_timestamp",
        "event_city": "event_city",
        "event_street": "event_street",
        "event_reason": "event_reason",
        "event_latitude": "event_latitude",
        "event_longitude": "event_longitude",
    }

    try:
        # Try to replace strings!
        _ = video_settings["text_overlay_format"].format(**replacement_strings)
    except KeyError as e:
        _LOGGER.error(
            "Bad string format: Invalid variable %s provided in --text_overlay_format",
            str(e),
        )
        return 1

    _LOGGER.debug("Video Settings %s", get_class_properties(video_settings))

    # If we constantly run and monitor for drive added or not.
    if video_settings["run_type"] in ["MONITOR", "MONITOR_ONCE"]:
        video_settings.update({"skip_existing": True})

        trigger_exist = False
        if monitor_file is None:
            print(
                f"{get_current_timestamp()}Monitoring for TeslaCam Drive to be "
                "inserted. Press CTRL-C to stop"
            )
        else:
            print(
                f"{get_current_timestamp()}Monitoring for trigger {monitor_file} to "
                "exist. Press CTRL-C to stop"
            )
        while True:
            try:
                # Monitoring for disk to be inserted and not for a file.
                if monitor_file is None:
                    source_folder, source_partition = get_tesladashcam_folder()
                    if source_folder is None:
                        # Nothing found, sleep for 1 minute and check again.
                        if trigger_exist:
                            print(
                                f"{get_current_timestamp()}TeslaCam drive has been "
                                "ejected."
                            )
                            print(
                                f"{get_current_timestamp()}Monitoring for TeslaCam "
                                "Drive to be inserted. Press CTRL-C to stop"
                            )

                        sleep(MONITOR_SLEEP_TIME)
                        trigger_exist = False
                        continue

                    # As long as TeslaCam drive is still attached we're going to
                    # keep on waiting.
                    if trigger_exist:
                        _LOGGER.debug("TeslaCam Drive still attached")
                        sleep(MONITOR_SLEEP_TIME)
                        continue

                    # Got a folder, append what was provided as source unless
                    # . was provided in which case everything is done.
                    source_folder_list = []
                    for folder in video_settings["source_folder"]:
                        if folder == ".":
                            source_folder_list.append(folder)
                        else:
                            source_folder_list.append(
                                os.path.join(source_folder, folder)
                            )

                    message = f"TeslaCam folder found on {source_partition}."
                else:
                    # Wait till trigger file exist (can also be folder).
                    if not os.path.exists(monitor_file):
                        _LOGGER.debug("Trigger file %s does not exist.", monitor_file)
                        sleep(MONITOR_SLEEP_TIME)
                        trigger_exist = False
                        continue

                    if trigger_exist:
                        sleep(MONITOR_SLEEP_TIME)
                        continue

                    message = "Trigger {monitor_file} exist."
                    trigger_exist = True

                    # Set monitor path, make sure what was provided is a file first
                    # otherwise get path.
                    monitor_path = monitor_file
                    if os.path.isfile(monitor_file):
                        monitor_path, _ = os.path.split(monitor_file)

                    # If . is provided then source folder is path where monitor file
                    # exist.
                    source_folder_list = []
                    for folder in video_settings["source_folder"]:
                        if folder == ".":
                            source_folder_list.append(monitor_path)
                        else:
                            # If source path provided is absolute then use that for
                            # source path
                            if os.path.isabs(folder):
                                source_folder_list.append(folder)
                            else:
                                # Path provided is relative, hence based on path of
                                # trigger file.
                                source_folder_list.append(
                                    os.path.join(monitor_path, folder)
                                )

                print(f"{get_current_timestamp()}{message}")
                if args.system_notification:
                    notify("TeslaCam", "Started", message)

                if len(source_folder_list) == 1:
                    print(
                        f"{get_current_timestamp()}Retrieving all files from "
                        f"{source_folder_list[0]}"
                    )
                else:
                    print(f"{get_current_timestamp()}Retrieving all files from: ")
                    for folder in source_folder_list:
                        print(
                            f"{get_current_timestamp()}                          "
                            f"{folder}"
                        )

                if video_settings["run_type"] == "MONITOR":
                    # We will continue to monitor hence we need to
                    # ensure we always have a unique final movie name.
                    movie_filename = (
                        datetime.today().strftime("%Y-%m-%d_%H_%M")
                        if video_settings["target_filename"] is None
                        else os.path.splitext(video_settings["target_filename"])[0]
                        + "_"
                        + datetime.today().strftime("%Y-%m-%d_%H_%M")
                        + os.path.splitext(video_settings["target_filename"])[1]
                    )
                else:
                    movie_filename = (
                        datetime.today().strftime("%Y-%m-%d_%H_%M")
                        if video_settings["target_filename"] is None
                        else video_settings["target_filename"]
                    )
                _LOGGER.debug(
                    "video_settings attribute movie_filename set to %s.", movie_filename
                )
                video_settings.update({"movie_filename": movie_filename})

                process_folders(source_folder_list, video_settings, args.delete_source)

                print(f"{get_current_timestamp()}Processing of movies has completed.")
                if args.system_notification:
                    notify(
                        "TeslaCam", "Completed", "Processing of movies has completed."
                    )

                # Stop if we're only to monitor once and then exit.
                if video_settings["run_type"] == "MONITOR_ONCE":
                    if monitor_file is not None:
                        if os.path.isfile(monitor_file):
                            try:
                                os.remove(monitor_file)
                            except OSError as exc:
                                print(
                                    f"{get_current_timestamp()}Error trying to remove "
                                    f"trigger file {monitor_file}: {exc}"
                                )

                    print(
                        f"{get_current_timestamp()}Exiting monitoring as asked process "
                        "once."
                    )
                    break

                if monitor_file is None:
                    trigger_exist = True
                    print(
                        f"{get_current_timestamp()}Waiting for TeslaCam Drive to be "
                        "ejected. Press CTRL-C to stop"
                    )
                else:
                    if os.path.isfile(monitor_file):
                        try:
                            os.remove(monitor_file)
                        except OSError as exc:
                            print(
                                f"{get_current_timestamp()}Error trying to remove "
                                f"trigger file {monitor_file}: {exc}"
                            )
                            break
                        trigger_exist = False

                        print(
                            f"{get_current_timestamp()}Monitoring for trigger "
                            f"{monitor_file}. Press CTRL-C to stop"
                        )
                    else:
                        print(
                            f"{get_current_timestamp()}Waiting for trigger "
                            f"{monitor_file} to be removed. "
                            f"Press CTRL-C to stop"
                        )

            except KeyboardInterrupt:
                print(f"{get_current_timestamp()}Monitoring stopped due to CTRL-C.")
                break
    else:
        movie_filename = (
            datetime.today().strftime("%Y-%m-%d_%H_%M")
            if video_settings["target_filename"] is None
            else video_settings["target_filename"]
        )
        _LOGGER.debug(
            "video_settings attribute movie_filename set to %s.", movie_filename
        )
        video_settings.update({"movie_filename": movie_filename})

        process_folders(
            video_settings["source_folder"], video_settings, args.delete_source
        )
    return 0


if sys.version_info < (3, 13):
    print(
        f"{get_current_timestamp()}Python version 3.8 or higher is required, you have: "
        f"{sys.version}. Please update your Python version."
    )
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
