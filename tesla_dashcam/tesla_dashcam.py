"""
Merges the 3 Tesla Dashcam and Sentry camera video files into 1 video. If
then further concatenates the files together to make 1 movie.
"""
import argparse
import logging
import os
import sys
from platform import processor as platform_processor
import json
from datetime import datetime, timedelta, timezone
from glob import glob, iglob
from pathlib import Path
from re import match, search, IGNORECASE as re_IGNORECASE
from shlex import split as shlex_split
from shutil import which
from subprocess import CalledProcessError, TimeoutExpired, run
from tempfile import mkstemp
from time import sleep, time as timestamp, mktime
from typing import List, Optional

import requests
from dateutil.parser import isoparse
from psutil import disk_partitions
from tzlocal import get_localzone

import staticmap

_LOGGER = logging.getLogger(__name__)

# TODO: Move everything into classes and separate files. For example,
#  update class, font class (for timestamp), folder class, clip class (
#  combining front, left, and right info), file class (for individual file).
#  Clip class would then have to merge the camera clips, folder class would
#  have to concatenate the merged clips. Settings class to take in all settings
# TODO: Create kind of logger or output classes for output. That then allows
#  different ones to be created based on where it should go to (stdout,
#  log file, ...).

VERSION = {"major": 0, "minor": 1, "patch": 18, "beta": -1}
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

# noinspection PyPep8
MOVIE_HOMEDIR = {
    "darwin": "Movies/Tesla_Dashcam",
    "win32": "Videos\Tesla_Dashcam",
    "cygwin": "Videos/Tesla_Dashcam",
    "linux": "Videos/Tesla_Dashcam",
    "freebsd11": "Videos/Tesla_Dashcam",
}

DEFAULT_CLIP_HEIGHT = 960
DEFAULT_CLIP_WIDTH = 1280

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

TOASTER_INSTANCE = None

display_ts = False

PLATFORM = sys.platform
# Allow setting for testing.
# PLATFORM = "darwin"
# PLATFORM = "win32"
# PLATFORM = "linux"

PROCESSOR = platform_processor()
if PLATFORM == "darwin" and PROCESSOR == "i386":
    try:
        sysctl = run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            timeout=120,
            text=True,
        )
    except TimeoutExpired:
        print("Timeout running sysctl")
    else:
        if sysctl.returncode == 0:
            if search("Apple", sysctl.stdout, re_IGNORECASE) is not None:
                PROCESSOR = "arm"
        else:
            print("Error running sysctl: {sysctl.returncode} - {sysctl.stderr}")

# Allow setting for testing.
# PROCESSOR = "arm"


class Camera_Clip(object):
    """ Camera Clip Class
    """

    def __init__(self, filename, timestamp, duration=0, include=False):
        self._filename = filename
        self._duration = duration
        self._timestamp = timestamp
        self._include = include

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    @property
    def duration(self):
        return self._duration if self._duration is not None else 0

    @duration.setter
    def duration(self, value):
        self._duration = value

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value

    @property
    def include(self):
        return self._include

    @include.setter
    def include(self, value):
        self._include = value

    @property
    def start_timestamp(self):
        return self.timestamp

    @property
    def end_timestamp(self):
        return self.start_timestamp + timedelta(seconds=self.duration)


class Clip(object):
    """ Clip Class
    """

    def __init__(self, timestamp=None, filename=None):
        self._timestamp = timestamp
        self._filename = filename
        self._start_timestamp = None
        self._end_timestamp = None
        self._duration = None
        self._cameras = {}

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    def camera(self, name):
        return self._cameras.get(name)

    def set_camera(self, name, camera_info: Camera_Clip):
        self._cameras.update({name: camera_info})

    @property
    def cameras(self):
        return self._cameras.items()

    def item(self, value):
        return self.camera(value)

    @property
    def items(self):
        return self.cameras

    @property
    def start_timestamp(self):
        if self._start_timestamp is not None:
            return self._start_timestamp
        if len(self.items) == 0:
            return datetime.now()

        for camera in self.sorted:
            if self.camera(camera).include:
                return self.camera(camera).start_timestamp
        return self.timestamp

    @start_timestamp.setter
    def start_timestamp(self, value):
        self._start_timestamp = value

    @property
    def end_timestamp(self):
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
    def end_timestamp(self, value):
        self._end_timestamp = value

    @property
    def duration(self):
        return (
            (self.end_timestamp - self.start_timestamp).total_seconds()
            if self._duration is None
            else self._duration
        )

    @duration.setter
    def duration(self, value):
        self._duration = value

    @property
    def sorted(self):
        return sorted(
            self._cameras, key=lambda camera: self._cameras[camera].start_timestamp
        )


class Event(object):
    """ Event Class """

    def __init__(self, folder, isfile=False, filename=None):
        self._folder = folder
        self._isFile = isfile
        self._filename = filename
        self._metadata = None
        self._start_timestamp = None
        self._end_timestamp = None
        self._duration = None
        self._clips = {}

    @property
    def folder(self):
        return self._folder

    @property
    def timestamp(self):
        return self.start_timestamp

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    @property
    def isfile(self):
        return self._isFile

    @isfile.setter
    def isfile(self, value):
        self._isFile = value

    def clip(self, timestamp):
        return self._clips.get(timestamp)

    def set_clip(self, timestamp, clip_info: Clip):
        self._clips.update({timestamp: clip_info})

    def item(self, value):
        return self.clip(value)

    @property
    def first_item(self):
        return self.clip(self.sorted[0])

    @property
    def items(self):
        return self._clips.items()

    @property
    def items_sorted(self):
        sorted_items = []
        for clip in self.sorted:
            sorted_items.append(self.clip(clip))
        return sorted_items

    @property
    def start_timestamp(self):
        if self._start_timestamp is not None:
            return self._start_timestamp
        if len(self.items) == 0:
            return datetime.now()

        return self.clip(self.sorted[0]).start_timestamp

    @start_timestamp.setter
    def start_timestamp(self, value):
        self._start_timestamp = value

    @property
    def end_timestamp(self):
        if self._end_timestamp is not None:
            return self._end_timestamp

        if len(self.items) == 0:
            return self.start_timestamp

        end_timestamp = self.clip(self.sorted[-1]).end_timestamp
        for _, clip_info in self.items:
            end_timestamp = (
                clip_info.end_timestamp
                if clip_info.end_timestamp > end_timestamp
                else end_timestamp
            )
        return end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, value):
        self._end_timestamp = value

    @property
    def duration(self):
        return (
            (self.end_timestamp - self.start_timestamp).total_seconds()
            if self._duration is None
            else self._duration
        )

    @duration.setter
    def duration(self, value):
        self._duration = value

    @property
    def count(self):
        return len(self._clips)

    @property
    def sorted(self):
        return sorted(self._clips, key=lambda clip: self._clips[clip].start_timestamp)

    def template(self, template, timestamp_format, video_settings):
        # This will also be called if no merging is going to occur (template = None) or
        # with an empty template (no grouping). In that case return "" as template.
        if template is None or template == "":
            return ""

        replacement_strings = {
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
            "event_city": self.metadata.get("city", "") or ""
            if self.metadata is not None
            else "",
            "event_reason": self.metadata.get("reason", "") or ""
            if self.metadata is not None
            else "",
            "event_latitude": self.metadata.get("latitude", "") or ""
            if self.metadata is not None
            else "",
            "event_longitude": self.metadata.get("longitude", "") or ""
            if self.metadata is not None
            else "",
        }

        if (
            self.metadata is not None
            and self.metadata.get("event_timestamp") is not None
        ):
            replacement_strings["event_timestamp"] = (
                self.metadata.get("event_timestamp")
                .astimezone(get_localzone())
                .strftime(timestamp_format)
            )

        try:
            # Try to replace strings!
            template = template.format(**replacement_strings)
        except KeyError as e:
            print(
                f"{get_current_timestamp()}Bad string format for merge template: Invalid variable {str(e)}"
            )
            template = None

        if template == "":
            template = (
                f"{self.start_timestamp.astimezone(get_localzone()).strftime(timestamp_format)} - "
                f"{self.end_timestamp.astimezone(get_localzone()).strftime(timestamp_format)}"
            )
        return template


class Movie(object):
    """ Movie Class """

    def __init__(self, filename=None):
        self._filename = filename
        self._start_timestamp = None
        self._end_timestamp = None
        self._duration = None
        self._events = {}

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    def event(self, folder):
        return self._events.get(folder)

    def set_event(self, event_info: Event):
        self._events.update({event_info.filename: event_info})

    def item(self, value):
        return self.event(value)

    @property
    def first_item(self):
        return self.event(self.sorted[0])

    @property
    def items(self):
        return self._events.items()

    @property
    def items_sorted(self):
        sorted_items = []
        for event in self.sorted:
            sorted_items.append(self.event(event))
        return sorted_items

    @property
    def start_timestamp(self):
        if self._start_timestamp is not None:
            return self._start_timestamp
        if len(self.items) == 0:
            return datetime.now()

        return self.event(self.sorted[0]).start_timestamp

    @start_timestamp.setter
    def start_timestamp(self, value):
        self._start_timestamp = value

    @property
    def end_timestamp(self):
        if self._end_timestamp is not None:
            return self._end_timestamp

        if len(self.items) == 0:
            return self.start_timestamp

        end_timestamp = self.event(self.sorted[-1]).end_timestamp
        for _, event_info in self.items:
            end_timestamp = (
                event_info.end_timestamp
                if event_info.end_timestamp > end_timestamp
                else end_timestamp
            )
        return end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, value):
        self._end_timestamp = value

    @property
    def duration(self):
        return (
            (self.end_timestamp - self.start_timestamp).total_seconds()
            if self._duration is None
            else self._duration
        )

    @duration.setter
    def duration(self, value):
        self._duration = value

    @property
    def count(self):
        return len(self._events)

    @property
    def count_clips(self):
        count = 0
        for _, event_info in self.items:
            count = count + event_info.count
        return count

    @property
    def sorted(self):
        return sorted(self._events, key=lambda clip: self._events[clip].start_timestamp)


class Font(object):
    """ Font Class
    """

    def __init__(self, layout, font=None, size=None, color=None):
        self._layout = layout
        self._font = font
        self._size = size
        self._color = color
        self._halign = None
        self._valign = None
        self._xpos = None
        self._ypos = None

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value

    @property
    def size(self):
        if hasattr(self._layout, "_font_size"):
            return getattr(self._layout, "_font_size")()

        return (
            int(max(16, 16 * self._layout.scale)) if self._size is None else self._size
        )

    @size.setter
    def size(self, value):
        self._size = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

    @property
    def halign(self):
        if hasattr(self._layout, "_font_halign"):
            return getattr(self._layout, "_font_halign")()

        return HALIGN.get(self._halign, self._halign)

    @halign.setter
    def halign(self, value):
        self._halign = value

    @property
    def valign(self):
        if hasattr(self._layout, "_font_valign"):
            return getattr(self._layout, "_font_valign")()

        return VALIGN.get(self._valign, self._valign)

    @valign.setter
    def valign(self, value):
        self._valign = value

    @property
    def xpos(self):
        return self._xpos

    @xpos.setter
    def xpos(self, value):
        self._xpos = value

    @property
    def ypos(self):
        return self._ypos

    @ypos.setter
    def ypos(self, value):
        self._ypos = value


class Camera(object):
    """ Camera Class
    """

    def __init__(self, layout, camera):
        self._layout = layout
        self._camera = camera
        self._include = True
        self._width = 1280
        self._height = 960
        self._xpos = 0
        self._ypos = 0
        self._scale = 0
        self._options = ""

    @property
    def camera(self):
        return self._camera

    @camera.setter
    def camera(self, value):
        self._camera = value

    @property
    def include(self):
        return self._include

    @include.setter
    def include(self, value):
        self._include = value

    @property
    def width(self):
        return (
            getattr(self._layout, "_" + self._camera + "_width")()
            if hasattr(self._layout, "_" + self._camera + "_width")
            else int(self._width * self.scale * self.include)
        )

    @width.setter
    def width(self, value):
        self._width = value

    @property
    def height(self):
        return (
            getattr(self._layout, "_" + self._camera + "_height")()
            if hasattr(self._layout, "_" + self._camera + "_height")
            else int(self._height * self.scale * self.include)
        )

    @height.setter
    def height(self, value):
        self._height = value

    @property
    def xpos(self):
        if hasattr(self._layout, "_" + self._camera + "_xpos"):
            return getattr(self._layout, "_" + self._camera + "_xpos")() * self.include

        return self._xpos * self.include

    @xpos.setter
    def xpos(self, value):
        self._xpos = value

    @property
    def ypos(self):
        if hasattr(self._layout, "_" + self._camera + "_ypos"):
            return getattr(self._layout, "_" + self._camera + "_ypos")() * self.include

        return self._ypos * self.include

    @ypos.setter
    def ypos(self, value):
        self._ypos = value

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        if value is None:
            self._scale = None
        elif len(str(value).split("x")) == 1:
            # Scale provided is a multiplier
            self._scale = float(str(value).split("x")[0])
        else:
            # Scale is a resolution.
            self.width = int(str(value).split("x")[0])
            self.height = int(str(value).split("x")[1])
            self._scale = 1

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value):
        self._options = value


class MovieLayout(object):
    """ Main Layout class
    """

    def __init__(self):
        self._cameras = {
            "Front": Camera(layout=self, camera="front"),
            "Left": Camera(layout=self, camera="left"),
            "Right": Camera(layout=self, camera="right"),
            "Rear": Camera(layout=self, camera="rear"),
        }
        self._font = Font(layout=self)

        self._swap_left_right = False
        self._swap_front_rear = False

        self._perspective = False

        self._font.halign = "CENTER"
        self._font.valign = "BOTTOM"

    def cameras(self, camera):
        return self._cameras.get(camera, self._cameras)

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value

    @property
    def swap_left_right(self):
        return self._swap_left_right

    @swap_left_right.setter
    def swap_left_right(self, value):
        self._swap_left_right = value

    @property
    def swap_front_rear(self):
        return self._swap_front_rear

    @swap_front_rear.setter
    def swap_front_rear(self, value):
        self._swap_front_rear = value

    @property
    def perspective(self):
        return self._perspective

    @perspective.setter
    def perspective(self, new_perspective):
        self._perspective = new_perspective

        if self._perspective:
            self.cameras("Left").options = (
                ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000, "
                "perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:"
                "x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination"
            )
            self.cameras("Right").options = (
                ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000,"
                "perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:"
                "x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination"
            )
        else:
            self.cameras("Left").options = ""
            self.cameras("Right").options = ""

    @property
    def scale(self):
        # Return scale of new video based on 1280x960 video = scale:1
        return (self.video_height * self.video_width) / (1280 * 960)

    @scale.setter
    def scale(self, scale):
        self.cameras("Front").scale = scale
        self.cameras("Left").scale = scale
        self.cameras("Right").scale = scale
        self.cameras("Rear").scale = scale

    @property
    def video_width(self):
        return int(
            max(
                self.cameras("Front").xpos + self.cameras("Front").width,
                self.cameras("Left").xpos + self.cameras("Left").width,
                self.cameras("Right").xpos + self.cameras("Right").width,
                self.cameras("Rear").xpos + self.cameras("Rear").width,
            )
        )

    @property
    def video_height(self):
        perspective_adjustement = 3 / 2 if self.perspective else 1
        return int(
            max(
                self.cameras("Front").ypos + self.cameras("Front").height,
                perspective_adjustement * self.cameras("Left").ypos
                + self.cameras("Left").height,
                perspective_adjustement * self.cameras("Right").ypos
                + self.cameras("Right").height,
                self.cameras("Rear").ypos + self.cameras("Rear").height,
            )
        )

    @property
    def center_xpos(self):
        return int(self.video_width / 2)

    @property
    def center_ypos(self):
        return int(self.video_height / 2)


class FullScreen(MovieLayout):
    """ FullScreen Movie Layout

                     [FRONT_CAMERA]
        [LEFT_CAMERA][REAR_CAMERA][RIGHT_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.scale = 1 / 2

    @property
    def video_width(self):
        return int(
            max(
                self.cameras("Front").width,
                self.cameras("Left").width
                + self.cameras("Rear").width
                + self.cameras("Right").width,
            )
        )

    @property
    def video_height(self):
        perspective_adjustement = 3 / 2 if self.perspective else 1
        return int(
            self.cameras("Front").height
            + max(
                perspective_adjustement * self.cameras("Left").height,
                self.cameras("Rear").height,
                perspective_adjustement * self.cameras("Right").height,
            )
        )

    def _front_height(self):
        # For height keep same ratio of 4/3
        return int(self.cameras("Front").width / 4 * 3)

    def _front_xpos(self):
        # Make sure that front is placed in the middle
        return (
            max(
                0,
                self.center_xpos
                - int(
                    (
                        self.cameras("Left").width
                        + self.cameras("Front").width
                        + self.cameras("Right").width
                    )
                    / 2
                )
                + self.cameras("Left").width,
            )
            * self.cameras("Front").include
        )

    def _left_xpos(self):
        return (
            max(
                0,
                self.center_xpos
                - int(
                    (
                        self.cameras("Left").width
                        + self.cameras("Rear").width
                        + self.cameras("Right").width
                    )
                    / 2
                ),
            )
            * self.cameras("Left").include
        )

    def _left_ypos(self):
        return (
            self.cameras("Front").ypos + self.cameras("Front").height
        ) * self.cameras("Left").include

    def _rear_xpos(self):
        return (
            max(
                0,
                self.center_xpos
                - int(
                    (
                        self.cameras("Left").width
                        + self.cameras("Rear").width
                        + self.cameras("Right").width
                    )
                    / 2
                )
                + self.cameras("Left").width,
            )
            * self.cameras("Rear").include
        )

    def _rear_ypos(self):
        return (
            self.cameras("Front").ypos + self.cameras("Front").height
        ) * self.cameras("Rear").include

    def _right_xpos(self):
        return (
            max(
                0,
                self.center_xpos
                - int(
                    (
                        self.cameras("Left").width
                        + self.cameras("Rear").width
                        + self.cameras("Right").width
                    )
                    / 2
                )
                + self.cameras("Left").width
                + self.cameras("Rear").width,
            )
            * self.cameras("Right").include
        )

    def _right_ypos(self):
        return (
            self.cameras("Front").ypos + self.cameras("Front").height
        ) * self.cameras("Right").include


# noinspection PyProtectedMember
class WideScreen(FullScreen):
    """ WideScreen Movie Layout

    [             FRONT_CAMERA             ]
    [LEFT_CAMERA][REAR_CAMERA][RIGHT_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.scale = 1 / 2
        # Set front scale to None so we know if it was overriden or not.
        self.cameras("Front").scale = None

    # Only front_width has to be adjusted as by default width would be left+rear+right instead of normal scale.
    def _front_width(self):
        return (
            (
                self.cameras("Left").width
                + self.cameras("Rear").width
                + self.cameras("Right").width
            )
            * self.cameras("Front").include
            if self.cameras("Front").scale is None
            else int(
                (
                    self.cameras("Front")._width
                    * self.cameras("Front").scale
                    * self.cameras("Front").include
                )
            )
        )


class Cross(FullScreen):
    """ Cross Movie Layout

             [FRONT_CAMERA]
        [LEFT_CAMERA][RIGHT_CAMERA]
             [REAR_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.scale = 1 / 2

    @property
    def video_width(self):
        return max(
            self.cameras("Front").width,
            self.cameras("Left").width + self.cameras("Right").width,
            self.cameras("Rear").width,
        )

    @property
    def video_height(self):
        if self.perspective:
            height = int(
                max(
                    3 / 2 * self.cameras("Left").height,
                    3 / 2 * self.cameras("Right").height,
                )
            )
            if (
                self.cameras("Left").include
                and self.cameras("Left").scale >= self.cameras("Rear").scale
                and self.cameras("Right").include
                and self.cameras("Right").scale >= self.cameras("Rear").scale
                and self.cameras("Rear").include
            ):
                height = int(height / 3 * 2)
            height += self.cameras("Rear").height
        else:
            height = (
                max(self.cameras("Left").height, self.cameras("Right").height)
                + self.cameras("Rear").height
            )

        return int(height + self.cameras("Front").height)

    def _front_xpos(self):
        return (
            int(max(0, self.center_xpos - (self.cameras("Front").width / 2)))
            * self.cameras("Front").include
        )

    def _left_xpos(self):
        return (
            max(
                0,
                self.center_xpos
                - int((self.cameras("Left").width + self.cameras("Right").width) / 2),
            )
            * self.cameras("Left").include
        )

    def _left_ypos(self):
        return (
            self.cameras("Front").height
            + int(
                (
                    max(self.cameras("Left").height, self.cameras("Right").height)
                    - self.cameras("Left").height
                )
                / 2
            )
        ) * self.cameras("Left").include

    def _right_xpos(self):
        return (
            max(
                0,
                self.center_xpos
                - int((self.cameras("Left").width + self.cameras("Right").width) / 2)
                + self.cameras("Left").width,
            )
            * self.cameras("Right").include
        )

    def _right_ypos(self):
        return (
            self.cameras("Front").height
            + int(
                (
                    max(self.cameras("Left").height, self.cameras("Right").height)
                    - self.cameras("Right").height
                )
                / 2
            )
        ) * self.cameras("Right").include

    def _rear_xpos(self):
        return (
            int(max(0, self.center_xpos - (self.cameras("Rear").width / 2)))
            * self.cameras("Rear").include
        )

    def _rear_ypos(self):
        return int(max(0, self.video_height - self.cameras("Rear").height))


# noinspection PyProtectedMember
class Diamond(Cross):
    """ Diamond Movie Layout

                    [FRONT_CAMERA]
        [LEFT_CAMERA]            [RIGHT_CAMERA]
                    [REAR_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.scale = 1 / 2

        self._font.valign = "MIDDLE"

    def _font_halign(self):
        if self._font._halign == "CENTER":
            # Change alignment to left or right if one of the left/right cameras is excluded.
            if (self.cameras("Left").include and not self.cameras("Right").include) or (
                self.cameras("Right").include and not self.cameras("Left").include
            ):
                x_pos = int(
                    max(
                        self.cameras("Front").xpos + self.cameras("Front").width / 2,
                        self.cameras("Rear").xpos + self.cameras("Rear").width / 2,
                    )
                )
                return f"({x_pos} - text_w / 2)"

        return HALIGN.get(self._font._halign, self._font._halign)

    def _font_valign(self):
        if self._font._valign == "MIDDLE":
            if self.cameras("Front").include:
                return (
                    f'({self.cameras("Front").ypos + self.cameras("Front").height} + 5)'
                )
            elif self.cameras("Rear").include:
                return f'({self.cameras("Rear").ypos} - 5 - text_h)'

        return VALIGN.get(self._font._valign, self._font._valign)

    def _font_size(self):
        # For this layout the video height has to include font size. But default for calculating
        # font size is based on video height.
        # Thus overriding font size to get video height without font size to figure our scaling.
        if self.font._size is None:
            scale = (
                self._video_height(include_fontsize=False)
                * self.video_width
                / (1280 * 960)
            )
            return int(max(16, 16 * scale))
        else:
            return self.font.size

    @property
    def video_width(self):
        return (
            max(self.cameras("Front").width, self.cameras("Rear").width)
            + self.cameras("Left").width
            + self.cameras("Right").width
        )

    def _video_height(self, include_fontsize=True):
        perspective = 3 / 2 if self.perspective else 1
        fontsize = self.font.size if include_fontsize else 0

        return int(
            max(
                perspective
                * max(self.cameras("Left").height, self.cameras("Right").height),
                self.cameras("Front").height + self.cameras("Rear").height + fontsize,
            )
        )

    @property
    def video_height(self):
        return self._video_height(include_fontsize=True)

    def _front_xpos(self):
        return (
            self.cameras("Left").width
            + int(
                (
                    max(self.cameras("Front").width, self.cameras("Rear").width)
                    - self.cameras("Front").width
                )
                / 2
            )
        ) * self.cameras("Front").include

    def _left_xpos(self):
        return 0

    def _left_ypos(self):
        return max(0, self.center_ypos - int(self.cameras("Left").height / 2))

    def _right_xpos(self):
        return max(
            self.cameras("Front").xpos + self.cameras("Front").width,
            self.cameras("Rear").xpos + self.cameras("Rear").width,
        )

    def _right_ypos(self):
        return max(0, self.center_ypos - int(self.cameras("Right").height / 2))

    def _rear_xpos(self):
        return (
            self.cameras("Left").width
            + int(
                (
                    max(self.cameras("Front").width, self.cameras("Rear").width)
                    - self.cameras("Rear").width
                )
                / 2
            )
        ) * self.cameras("Rear").include


class MyArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, arg_line):
        # Remove comments.
        return shlex_split(arg_line, comments=True)

    def args_to_dict(self, arguments, default):
        argument_list = []

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


# noinspection PyCallByClass,PyProtectedMember
class SmartFormatter(argparse.HelpFormatter):
    """ Formatter for argument help. """

    def _split_lines(self, text, width):
        """ Provide raw output allowing for prettier help output """
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)

    def _get_help_string(self, action):
        """ Call default help string """
        return argparse.ArgumentDefaultsHelpFormatter._get_help_string(self, action)


def search_dict(
    match_value: object = None, key: str = None, search_list: List[dict] = None
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
    if key is None or search_list is None:
        return None

    if match_value is None:
        return next(
            (element for element in search_list if element.get(key) is None), None
        )

    return next(
        (element for element in search_list if element.get(key) == match_value), None
    )


def get_current_timestamp():
    """Returns the current timestamp"""
    """Uses ugly global variable, this should die a quick death..."""
    """Preferably, a text output class should be created and the value stored there."""
    if display_ts:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S - ")
    else:
        return ""


def check_latest_release(include_beta):
    """ Checks GitHub for latest release """

    url = f"{GITHUB['URL']}/repos/{GITHUB['owner']}/{GITHUB['repo']}/releases"

    if not include_beta:
        url = url + "/latest"
    try:
        releases = requests.get(url)
    except requests.exceptions.RequestException as exc:
        print(f"{get_current_timestamp()}Unable to check for latest release: {exc}")
        return None

    release_data = releases.json()
    # If we include betas then we would have received a list, thus get 1st
    # element as that is the latest release.
    if include_beta:
        release_data = release_data[0]

    return release_data


def get_tesladashcam_folder():
    """ Check if there is a drive mounted with the Tesla DashCam folder."""
    for partition in disk_partitions(all=False):
        if "cdrom" in partition.opts or partition.fstype == "":
            continue

        teslacamfolder = os.path.join(partition.mountpoint, "TeslaCam")
        if os.path.isdir(teslacamfolder):
            _LOGGER.debug(f"Folder TeslaCam found on partition {partition.mountpoint}.")
            return teslacamfolder, partition.mountpoint
        _LOGGER.debug(f"No TeslaCam folder on partition {partition.mountpoint}.")
    return None, None


def get_movie_files(source_folder, video_settings):
    """ Find all the clip files within folder (and subfolder if requested)


    """

    # Making as a set to ensure uniqueness.
    folder_list = set()
    # Determine all the folders to scan for files. Using a SET ensuring uniqueness for the folders.
    _LOGGER.debug(f"Determining all the folders to scan for video files")
    for source_pathname in source_folder:
        _LOGGER.debug(f"Processing provided source path {source_pathname}.")
        for pathname in iglob(os.path.expanduser(os.path.expandvars(source_pathname))):
            _LOGGER.debug(f"Processing {pathname}.")
            if (
                os.path.isdir(pathname)
                or os.path.ismount(pathname)
                and not video_settings["exclude_subdirs"]
            ):
                _LOGGER.debug(f"Retrieving all subfolders for {pathname}.")
                for folder, _, _ in os.walk(pathname, followlinks=True):
                    folder_list.add(folder)
            else:
                folder_list.add(pathname)

    events_list = {}
    # Go through each folder, get the movie files within it and add to movie list.
    # Sorting folder list 1st.
    print(f"{get_current_timestamp()}Scanning {len(folder_list)} folder(s)")
    folders_scanned = 0
    for event_folder in sorted(folder_list):
        if folders_scanned % 10 == 0 and folders_scanned != 0:
            print(f"Scanned {folders_scanned}/{len(folder_list)}.")
        folders_scanned = folders_scanned + 1

        if os.path.isdir(event_folder):
            _LOGGER.debug(f"Retrieving all video files in folder {event_folder}.")
            event_info = None

            # Collect video files within folder and process.
            for clip_filename in glob(os.path.join(event_folder, "*.mp4")):
                # Get the timestamp of the filename.
                _, clip_filename_only = os.path.split(clip_filename)
                clip_timestamp = clip_filename_only.rsplit("-", 1)[0]

                # Check if we already processed this timestamp.
                if (
                    event_info is not None
                    and event_info.clip(clip_timestamp) is not None
                ):
                    # Already processed this clip, moving on.
                    continue

                front_filename = str(clip_timestamp) + "-front.mp4"
                front_path = os.path.join(event_folder, front_filename)

                left_filename = str(clip_timestamp) + "-left_repeater.mp4"
                left_path = os.path.join(event_folder, left_filename)

                right_filename = str(clip_timestamp) + "-right_repeater.mp4"
                right_path = os.path.join(event_folder, right_filename)

                rear_filename = str(clip_timestamp) + "-back.mp4"
                rear_path = os.path.join(event_folder, rear_filename)

                # Get meta data for each camera for this timestamp to determine creation time and duration.
                metadata = get_metadata(
                    video_settings["ffmpeg_exec"],
                    [front_path, left_path, right_path, rear_path],
                )

                # Move on to next one if nothing received.
                if not metadata:
                    _LOGGER.debug(
                        f"No camera files in folder {event_folder} with timestamp "
                        f"{clip_timestamp} found."
                    )
                    continue

                clip_info = None
                clip_starting_timestamp = datetime.now()
                # Store filename, duration, timestamp, and if has to be included for each camera
                for item in metadata:
                    _, filename = os.path.split(item["filename"])
                    if filename == front_filename:
                        camera = "Front"
                    elif filename == left_filename:
                        camera = "Left"
                    elif filename == right_filename:
                        camera = "Right"
                    elif filename == rear_filename:
                        camera = "Rear"
                    else:
                        continue

                    if clip_info is None:
                        # We get the clip starting time from the filename and provided that as initial timestamp.
                        if len(clip_timestamp) == 16:
                            # This is for before version 2019.16
                            clip_starting_timestamp = datetime.strptime(
                                clip_timestamp, "%Y-%m-%d_%H-%M"
                            )
                            clip_starting_timestamp = clip_starting_timestamp.astimezone(
                                get_localzone()
                            )
                        else:
                            # This is for version 2019.16 and later
                            clip_starting_timestamp = datetime.strptime(
                                clip_timestamp, "%Y-%m-%d_%H-%M-%S"
                            )
                            clip_starting_timestamp = clip_starting_timestamp.astimezone(
                                timezone.utc
                            )
                        clip_info = Clip(timestamp=clip_starting_timestamp)

                    clip_camera_info = Camera_Clip(
                        filename=filename,
                        duration=item["duration"],
                        timestamp=(
                            item["timestamp"]
                            if item["timestamp"] is not None
                            else clip_starting_timestamp
                        ),
                        include=(
                            item["include"]
                            if video_settings["video_layout"].cameras(camera).include
                            else False
                        ),
                    )

                    # Store the camera information in the clip.
                    clip_info.set_camera(camera, clip_camera_info)

                # Not storing anything if no cameras included for this clip.
                if clip_info is None:
                    _LOGGER.debug(
                        f"No valid camera files in folder {event_folder} with timestamp "
                        f"{clip_timestamp}"
                    )
                    continue

                # Store the clip information in the event
                if event_info is None:
                    event_info = Event(folder=event_folder)
                event_info.set_clip(clip_timestamp, clip_info)

            # Got all the clip information for this event (folder)
            # If no clips found then skip this folder and continue on.
            if event_info is None:
                _LOGGER.debug(f"No clips found in folder {event_folder}")
                continue

            _LOGGER.debug(f"Found {event_info.count} clips in folder {event_folder}")
            # We have clips for this event, get the event meta data.
            event_metadata = None
            event_metadata_file = os.path.join(event_folder, "event.json")
            if os.path.isfile(event_metadata_file):
                _LOGGER.debug(f"Folder {event_folder} has an event file.")
                try:
                    with open(event_metadata_file) as f:
                        try:
                            event_file_data = json.load(f)

                            event_timestamp = event_file_data.get("timestamp")
                            if event_timestamp is not None:
                                # Convert string to timestamp.
                                try:
                                    event_timestamp = datetime.strptime(
                                        event_timestamp, "%Y-%m-%dT%H:%M:%S"
                                    )
                                    event_timestamp = event_timestamp.astimezone(
                                        timezone.utc
                                    )
                                except ValueError as e:
                                    _LOGGER.warning(
                                        f"Event timestamp ({event_timestamp}) found in "
                                        f"{event_metadata_file} could not be parsed as a timestamp"
                                    )
                                    event_timestamp = None

                            event_metadata = {
                                "event_timestamp": event_timestamp,
                                "city": event_file_data.get("city"),
                                "latitude": None,
                                "longitude": None,
                                "reason": EVENT_REASON.get(
                                    event_file_data.get("reason")
                                ),
                            }
                            if event_metadata["reason"] is None:
                                for event_reason in EVENT_REASON:
                                    if match(
                                        event_reason, event_file_data.get("reason")
                                    ):
                                        event_metadata["reason"] = EVENT_REASON.get(
                                            event_reason
                                        )
                                        break

                            event_latitude = event_file_data.get("est_lat")
                            if event_latitude is not None:
                                try:
                                    event_latitude = float(event_latitude)
                                except ValueError as e:
                                    pass
                            event_metadata["latitude"] = event_latitude

                            event_longitude = event_file_data.get("est_lon")
                            if event_longitude is not None:
                                try:
                                    event_longitude = float(event_longitude)
                                except ValueError as e:
                                    pass
                            event_metadata["longitude"] = event_longitude

                        except json.JSONDecodeError as e:
                            _LOGGER.warning(
                                f"Event JSON found in {event_metadata_file} failed to parse "
                                f"with JSON error: {str(e)}"
                            )
                except:
                    pass

            # Store the event data in the event.
            event_info.metadata = event_metadata
        else:
            _LOGGER.debug(f"Adding video file {event_folder}.")
            # Get the metadata for this video files.
            metadata = get_metadata(video_settings["ffmpeg_exec"], [event_folder])
            # Store video as a camera clip.
            clip_timestamp = (
                metadata[0]["timestamp"]
                if metadata[0]["timestamp"] is not None
                else datetime.fromtimestamp(os.path.getmtime(event_folder))
            )

            clip_camera_info = Camera_Clip(
                filename=event_folder,
                duration=metadata[0]["duration"],
                timestamp=clip_timestamp
                if clip_timestamp is not None
                else datetime.now(),
                include=True,
            )
            # Add it as a clip
            clip_info = Clip(timestamp=clip_camera_info.timestamp)
            clip_info.set_camera("FULL", clip_camera_info)
            # And now store as an event.
            event_info = Event(folder=event_folder, isfile=True, filename=event_folder)

        # Now add the event folder to our events list.
        events_list.update({event_folder: event_info})

    _LOGGER.debug(f"{len(events_list)} folders contain clips.")
    return events_list


def get_metadata(ffmpeg, filenames):
    """ Retrieve the meta data for the clip (i.e. timestamp, duration) """
    # Get meta data for each video to determine creation time and duration.
    ffmpeg_command = [ffmpeg]

    metadata = []
    for camera_file in filenames:
        if os.path.isfile(camera_file):
            ffmpeg_command.append("-i")
            ffmpeg_command.append(camera_file)
            metadata.append(
                {
                    "filename": camera_file,
                    "timestamp": None,
                    "duration": 0,
                    "include": False,
                }
            )
        else:
            _LOGGER.debug(f"File {camera_file} does not exist, skipping.")

    # Don't run ffmpeg if nothing to check for.
    if not metadata:
        return metadata

    ffmpeg_command.append("-hide_banner")

    command_result = run(ffmpeg_command, capture_output=True, text=True)
    metadata_iterator = iter(metadata)
    input_counter = 0

    video_timestamp = None
    wait_for_input_line = True
    metadata_item = {}
    for line in command_result.stderr.splitlines():
        if search("^Input #", line) is not None:
            # If filename was not yet appended then it means it is a corrupt file, in that case just add to list for
            # but identify not to include for processing
            metadata_item = next(metadata_iterator)

            input_counter += 1
            video_timestamp = None
            wait_for_input_line = False
            continue

        if wait_for_input_line:
            continue

        if search("^ *creation_time ", line) is not None:
            line_split = line.split(":", 1)
            video_timestamp = datetime.strptime(
                line_split[1].strip(), "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            continue

        if search("^ *Duration: ", line) is not None:
            line_split = line.split(",")
            line_split = line_split[0].split(":", 1)
            duration_list = line_split[1].split(":")
            duration = (
                int(duration_list[0]) * 60 * 60
                + int(duration_list[1]) * 60
                + int(duration_list[2].split(".")[0])
                + (float(duration_list[2].split(".")[1]) / 100)
            )
            # File will only be processed if duration is greater then 0
            include = duration > 0

            if video_timestamp is None:
                _LOGGER.warning(
                    f"Did not find a creation_time in metadata for "
                    f"file {metadata_item['filename']}"
                )

            metadata_item.update(
                {"timestamp": video_timestamp, "duration": duration, "include": include}
            )

            wait_for_input_line = True

    return metadata


def create_intermediate_movie(
    event_info: Event, clip_info: Clip, folder_timestamps, video_settings, clip_number
):
    """ Create intermediate movie files. This is the merging of the 3 camera

    video files into 1 video file. """
    # We first stack (combine the 3 different camera video files into 1
    # and then we concatenate.
    front_camera = None
    left_camera = None
    right_camera = None
    rear_camera = None

    for camera_name, camera_info in clip_info.cameras:
        if camera_info.include:
            camera_filename = os.path.join(event_info.folder, camera_info.filename)
            if camera_name == "Front":
                front_camera = camera_filename
            elif camera_name == "Left":
                left_camera = camera_filename
            elif camera_name == "Right":
                right_camera = camera_filename
            elif camera_name == "Rear":
                rear_camera = camera_filename

    if (
        front_camera is None
        and left_camera is None
        and right_camera is None
        and rear_camera is None
    ):
        _LOGGER.debug(
            f"No valid front, left, right, and rear camera clip exist for "
            f'{clip_info.timestamp.astimezone(get_localzone()).strftime("%Y-%m-%dT%H-%M-%S")}'
        )
        return True

    if video_settings["video_layout"].swap_left_right:
        left_camera, right_camera = right_camera, left_camera

    if video_settings["video_layout"].swap_front_rear:
        front_camera, rear_camera = rear_camera, front_camera

    # Determine if this clip is to be included based on potential start and end timestamp/offsets that were provided.
    # Clip starting time is between the start&end times we're looking for
    # or Clip end time is between the start&end time we're looking for.
    # or Starting time is between start&end clip time
    # or End time is between start&end clip time
    starting_timestamp = clip_info.start_timestamp
    ending_timestamp = clip_info.end_timestamp
    if not (
        folder_timestamps[0] <= starting_timestamp <= folder_timestamps[1]
        or folder_timestamps[0] <= ending_timestamp <= folder_timestamps[1]
        or starting_timestamp <= folder_timestamps[0] <= ending_timestamp
        or starting_timestamp <= folder_timestamps[1] <= ending_timestamp
    ):
        # This clip is not in-between the timestamps we want, skip it.
        _LOGGER.debug(
            f"Clip timestamp from {starting_timestamp} to {ending_timestamp} not "
            f"between {folder_timestamps[0]} and {folder_timestamps[1]}"
        )
        return True

    # Determine if we need to do an offset of the starting timestamp
    ffmpeg_offset_command = []
    clip_duration = clip_info.duration

    # This clip falls in between the start and end timestamps to include.
    # Set offsets if required
    if starting_timestamp < folder_timestamps[0]:
        # Starting timestamp is withing this clip.
        starting_offset = (folder_timestamps[0] - starting_timestamp).total_seconds()
        starting_timestamp = folder_timestamps[0]
        clip_duration = (ending_timestamp - starting_timestamp).total_seconds()
        ffmpeg_offset_command = ["-ss", str(starting_offset)]
        _LOGGER.debug(
            f"Clip start offset by {starting_offset} seconds due to start timestamp "
            f"requested."
        )

    # Adjust duration if end of clip's timestamp is after ending timestamp we need.
    if ending_timestamp > folder_timestamps[1]:
        ending_timestamp = folder_timestamps[1]
        prev_clip_duration = clip_duration
        clip_duration = (ending_timestamp - starting_timestamp).total_seconds()
        ffmpeg_offset_command += ["-t", str(clip_duration)]
        _LOGGER.debug(
            f"Clip duration reduced from {prev_clip_duration} "
            f"to {clip_duration} seconds due to end timestamp requested."
        )

    # Make sure our duration does not end up with 0, if it does then do not continue.
    if clip_duration <= 0:
        _LOGGER.debug(
            f"Clip duration is {clip_duration}, not processing as no valid video."
        )
        return True

    # Confirm if files exist, if not replace with nullsrc
    input_count = 0
    if left_camera is not None:
        ffmpeg_left_command = ffmpeg_offset_command + ["-i", left_camera]
        ffmpeg_left_camera = (
            ";[" + str(input_count) + ":v] " + video_settings["left_camera"]
        )
        input_count += 1
    else:
        ffmpeg_left_command = []
        ffmpeg_left_camera = (
            video_settings["background"].format(
                duration=clip_duration,
                speed=video_settings["movie_speed"],
                width=video_settings["video_layout"].cameras("Left").width,
                height=video_settings["video_layout"].cameras("Left").height,
            )
            + "[left]"
            if video_settings["video_layout"].cameras("Left").include
            else ""
        )

    if front_camera is not None:
        ffmpeg_front_command = ffmpeg_offset_command + ["-i", front_camera]
        ffmpeg_front_camera = (
            ";[" + str(input_count) + ":v] " + video_settings["front_camera"]
        )
        input_count += 1
    else:
        ffmpeg_front_command = []
        ffmpeg_front_camera = (
            video_settings["background"].format(
                duration=clip_duration,
                speed=video_settings["movie_speed"],
                width=video_settings["video_layout"].cameras("Front").width,
                height=video_settings["video_layout"].cameras("Front").height,
            )
            + "[front]"
            if video_settings["video_layout"].cameras("Front").include
            else ""
        )

    if right_camera is not None:
        ffmpeg_right_command = ffmpeg_offset_command + ["-i", right_camera]
        ffmpeg_right_camera = (
            ";[" + str(input_count) + ":v] " + video_settings["right_camera"]
        )
        input_count += 1
    else:
        ffmpeg_right_command = []
        ffmpeg_right_camera = (
            video_settings["background"].format(
                duration=clip_duration,
                speed=video_settings["movie_speed"],
                width=video_settings["video_layout"].cameras("Right").width,
                height=video_settings["video_layout"].cameras("Right").height,
            )
            + "[right]"
            if video_settings["video_layout"].cameras("Right").include
            else ""
        )

    if rear_camera is not None:
        ffmpeg_rear_command = ffmpeg_offset_command + ["-i", rear_camera]
        ffmpeg_rear_camera = (
            ";[" + str(input_count) + ":v] " + video_settings["rear_camera"]
        )
        input_count += 1
    else:
        ffmpeg_rear_command = []
        ffmpeg_rear_camera = (
            video_settings["background"].format(
                duration=clip_duration,
                speed=video_settings["movie_speed"],
                width=video_settings["video_layout"].cameras("Rear").width,
                height=video_settings["video_layout"].cameras("Rear").height,
            )
            + "[rear]"
            if video_settings["video_layout"].cameras("Rear").include
            else ""
        )

    local_timestamp = clip_info.timestamp.astimezone(get_localzone())

    # Check if target video file exist if skip existing.
    file_already_exist = False
    if video_settings["skip_existing"]:
        temp_movie_name = (
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
                f"{get_current_timestamp()}\t\tSkipping clip {clip_number + 1}/{event_info.count} from "
                f"{local_timestamp.strftime('%x %X')} and {int(clip_duration)} seconds as it already exist."
            )
            clip_info.filename = temp_movie_name
            clip_info.start_timestamp = starting_timestamp
            clip_info.end_timestamp = ending_timestamp
            # Get actual duration of our new video, required for chapters when concatenating.
            metadata = get_metadata(video_settings["ffmpeg_exec"], [temp_movie_name])
            clip_info.duration = metadata[0]["duration"] if metadata else None

            return True
    else:
        target_folder = (
            video_settings["temp_dir"]
            if not video_settings["keep_intermediate"]
            and video_settings["temp_dir"] is not None
            else video_settings["target_folder"]
        )
        temp_movie_name = os.path.join(
            target_folder, local_timestamp.strftime("%Y-%m-%dT%H-%M-%S") + ".mp4"
        )

    print(
        f"{get_current_timestamp()}\t\tProcessing clip {clip_number + 1}/{event_info.count} from "
        f"{local_timestamp.strftime('%x %X')} and {int(clip_duration)} seconds long."
    )

    starting_epoch_timestamp = int(starting_timestamp.timestamp())

    ffmpeg_text = video_settings["ffmpeg_text_overlay"]
    user_formatted_text = video_settings["text_overlay_format"]
    user_timestamp_format = video_settings["timestamp_format"]
    ffmpeg_user_timestamp_format = user_timestamp_format.replace(":", "\\\:")

    # Replace variables in user provided text overlay
    replacement_strings = {
        "start_timestamp": starting_timestamp.astimezone(get_localzone()).strftime(
            user_timestamp_format
        ),
        "end_timestamp": ending_timestamp.astimezone(get_localzone()).strftime(
            user_timestamp_format
        ),
        "local_timestamp_rolling": f"%{{pts:localtime:{starting_epoch_timestamp}:{ffmpeg_user_timestamp_format}}}",
        "event_timestamp_countdown": "n/a",
        "event_timestamp_countdown_rolling": "n/a",
        "event_timestamp": "n/a",
        "event_city": "n/a",
        "event_reason": "n/a",
        "event_latitude": 0.0,
        "event_longitude": 0.0,
    }

    if event_info.metadata is not None:
        if event_info.metadata["event_timestamp"] is not None:
            event_epoch_timestamp = int(
                event_info.metadata["event_timestamp"].timestamp()
            )
            replacement_strings["event_timestamp"] = (
                event_info.metadata["event_timestamp"]
                .astimezone(get_localzone())
                .strftime(user_timestamp_format)
            )

            # Calculate the time until the event
            replacement_strings["event_timestamp_countdown"] = (
                starting_epoch_timestamp - event_epoch_timestamp
            )
            replacement_strings[
                "event_timestamp_countdown_rolling"
            ] = "%{{pts:hms:{event_timestamp_countdown}}}".format(
                event_timestamp_countdown=replacement_strings[
                    "event_timestamp_countdown"
                ]
            )

        replacement_strings["event_city"] = event_info.metadata["city"] or "n/a"
        replacement_strings["event_reason"] = event_info.metadata["reason"] or "n/a"
        replacement_strings["event_latitude"] = event_info.metadata["latitude"] or 0.0
        replacement_strings["event_longitude"] = event_info.metadata["longitude"] or 0.0

    try:
        # Try to replace strings!
        user_formatted_text = user_formatted_text.format(**replacement_strings)
    except KeyError as e:
        user_formatted_text = "Bad string format: Invalid variable {stderr}".format(
            stderr=str(e)
        )
        _LOGGER.warning(user_formatted_text)

    # Escape characters ffmpeg needs
    user_formatted_text = user_formatted_text.replace(":", "\:")
    user_formatted_text = user_formatted_text.replace("\\n", os.linesep)

    ffmpeg_text = ffmpeg_text.replace("__USERTEXT__", user_formatted_text)

    ffmpeg_filter = (
        video_settings["base"].format(
            duration=clip_duration, speed=video_settings["movie_speed"]
        )
        + ffmpeg_left_camera
        + ffmpeg_front_camera
        + ffmpeg_right_camera
        + ffmpeg_rear_camera
        + video_settings["clip_positions"]
        + ffmpeg_text
        + video_settings["ffmpeg_speed"]
        + video_settings["ffmpeg_motiononly"]
    )

    title_timestamp = (
        event_info.metadata["event_timestamp"]
        .astimezone(get_localzone())
        .strftime(user_timestamp_format)
        if event_info.metadata["reason"] == "SENTRY"
        and event_info.metadata["event_timestamp"] is not None
        else starting_timestamp.astimezone(get_localzone()).strftime(
            user_timestamp_format
        )
    )
    title = (
        f"{event_info.metadata.get('reason')}: {title_timestamp}"
        if event_info.metadata.get("reason") is not None
        else title_timestamp
    )

    ffmpeg_metadata = [
        "-metadata",
        f"creation_time={starting_timestamp.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000000Z')}",
        "-metadata",
        f"description=Created by tesla_dashcam {VERSION_STR}",
        "-metadata",
        f"title={title}",
    ]

    ffmpeg_command = (
        [video_settings["ffmpeg_exec"]]
        + ["-loglevel", "info"]
        + ffmpeg_left_command
        + ffmpeg_front_command
        + ffmpeg_right_command
        + ffmpeg_rear_command
        + ["-filter_complex", ffmpeg_filter]
        + ["-map", f"[{video_settings['input_clip']}]"]
        + video_settings["other_params"]
        + ffmpeg_metadata
    )

    ffmpeg_command = ffmpeg_command + ["-y", temp_movie_name]
    _LOGGER.debug(f"FFMPEG Command: {ffmpeg_command}")
    # Run the command.
    try:
        ffmpeg_output = run(
            ffmpeg_command, capture_output=True, check=True, universal_newlines=True
        )
    except CalledProcessError as exc:
        print(
            f"{get_current_timestamp()}\t\t\tError trying to create clip for "
            f"{os.path.join(event_info.folder, local_timestamp.strftime('%Y-%m-%dT%H-%M-%S') + '.mp4')}."
            f"RC: {exc.returncode}\n"
            f"{get_current_timestamp()}\t\t\tCommand: {exc.cmd}\n"
            f"{get_current_timestamp()}\t\t\tError: {exc.stderr}\n\n"
        )
        return False
    _LOGGER.debug("FFMPEG output:\n %s", ffmpeg_output.stdout)
    _LOGGER.debug("FFMPEG error output:\n %s", ffmpeg_output.stderr)

    clip_info.filename = temp_movie_name
    clip_info.start_timestamp = starting_timestamp
    clip_info.end_timestamp = ending_timestamp
    # Get actual duration of our new video, required for chapters when concatenating.
    metadata = get_metadata(video_settings["ffmpeg_exec"], [temp_movie_name])
    clip_info.duration = metadata[0]["duration"] if metadata else None

    return True


def create_title_screen(events, video_settings):
    """ Create a map centered around the event """
    _LOGGER.debug(f"Creating map based on {len(events)}")
    if events == None or len(events) == 0:
        _LOGGER.debug("No events provided to create map for.")
        return None

    m = staticmap.StaticMap(
        video_settings["video_layout"].video_width,
        video_settings["video_layout"].video_height,
    )

    coordinates = []
    for event in events:
        try:
            lon = float(event.metadata["longitude"])
            lat = float(event.metadata["latitude"])
        except:
            _LOGGER.debug(
                f"Error trying to convert {event.metadata['longitude']} or {event.metadata['latitude']} into a float"
            )
            continue

        # Sometimes event info has a very small (i.e. 2.35754e-311) or 0 value, we ignore if both are 0.
        # 0,0 is in the ocean near Africa.
        if round(lon, 5) == 0 and round(lat, 5) == 0:
            _LOGGER.debug(
                f"Skipping as longitude {lon} and/or latidude {lat} are invalid."
            )
            continue

        coordinate = [lon, lat]
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
    movie, event_info, movie_filename, video_settings, chapter_offset, title_screen_map
):
    """ Concatenate provided movie files into 1."""
    # Just return if there are no clips.
    if movie.count <= 0:
        _LOGGER.debug(f"Movie list is empty")
        return True

    title_video_filename = None
    if title_screen_map:
        title_image = create_title_screen(
            events=event_info, video_settings=video_settings
        )

        title_image_filename = None
        if title_image is not None:
            _, title_image_filename = mkstemp(suffix=".png", text=False)

            try:
                title_image.save(title_image_filename)
            except (ValueError, OSError) as exc:
                print(
                    f"{get_current_timestamp()}\t\t\tError trying to save title image. RC: {str(exc)}"
                )
                title_image_filename = None
            else:
                _LOGGER.debug(f"Title image saved to {title_image_filename}")

        if title_image_filename is not None:
            _, title_video_filename = mkstemp(suffix=".mp4", text=False)
            _LOGGER.debug(f"Creating movie for title image to {title_video_filename}")
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
                f"scale={video_settings['video_layout'].video_width}x{video_settings['video_layout'].video_height}",
                #                "-pix_fmt",
                #                "yuv420p",
            ]

            ffmpeg_command = (
                [video_settings["ffmpeg_exec"]]
                + ["-loglevel", "info"]
                + ffmpeg_params
                + video_settings["other_params"]
            )

            ffmpeg_command = ffmpeg_command + ["-y", title_video_filename]

            _LOGGER.debug(f"FFMPEG Command: {ffmpeg_command}")
            try:
                ffmpeg_output = run(
                    ffmpeg_command,
                    capture_output=True,
                    check=True,
                    universal_newlines=True,
                )
            except CalledProcessError as exc:
                print(
                    f"{get_current_timestamp()}\t\t\tError trying to create title clip. RC: {exc.returncode}\n"
                    f"{get_current_timestamp()}\t\t\tCommand: {exc.cmd}\n"
                    f"{get_current_timestamp()}\t\t\tError: {exc.stderr}\n\n"
                )
                title_video_filename = None

                # Now remove the title image
                try:
                    os.remove(title_image_filename)
                except:
                    _LOGGER.debug(f"Failed to remove {title_image_filename}")
                    pass
            else:
                _LOGGER.debug("FFMPEG output:\n %s", ffmpeg_output.stdout)
                _LOGGER.debug("FFMPEG error output:\n %s", ffmpeg_output.stderr)

    # Go through the list of clips to create the command and content for chapter meta file.
    total_clips = 0
    meta_content = ""
    file_content = ""
    meta_start = 0
    total_videoduration = 0
    start_timestamp = None
    end_timestamp = None
    chapter_offset = chapter_offset * 1000000000

    if title_video_filename:
        file_content = (
            f"file 'file:{title_video_filename.replace(os.sep, '/')}'{os.linesep}"
        )
        total_videoduration += 3 * 1000000000
        meta_start += 3 * 1000000000 + 1

    # Loop through the list sorted by video timestamp.
    for movie_item in movie.sorted:
        video_clip = movie.item(movie_item)
        # Check that this item was included for processing or not.
        if video_clip.filename is None:
            continue

        if not os.path.isfile(video_clip.filename):
            print(
                f"{get_current_timestamp()}\t\tFile {video_clip.filename} does not exist anymore, skipping."
            )
            continue
        _LOGGER.debug(
            f"Video file {video_clip.filename} will be added to " f"{movie_filename}"
        )
        # Add this file in our join list.
        # NOTE: Recent ffmpeg changes requires Windows paths in this file to look like
        # file 'file:<actual path>'
        # https://trac.ffmpeg.org/ticket/2702
        file_content = (
            file_content
            + f"file 'file:{video_clip.filename.replace(os.sep, '/')}'{os.linesep}"
        )
        total_clips = total_clips + 1
        title = video_clip.start_timestamp.astimezone(get_localzone())
        # For duration need to also calculate if video was sped-up or slowed down.
        video_duration = int(video_clip.duration * 1000000000)
        total_videoduration += video_duration
        chapter_start = meta_start
        if video_duration > abs(chapter_offset):
            if chapter_offset < 0:
                chapter_start = meta_start + video_duration + chapter_offset
            elif chapter_offset > 0:
                chapter_start = chapter_start + chapter_offset

        # We need to add an initial chapter if our "1st" chapter is not at the beginning of the movie.
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
            f"title={title.strftime(video_settings['timestamp_format'])}{os.linesep}"
        )
        meta_start = meta_start + 1 + video_duration

        if start_timestamp is None:
            start_timestamp = video_clip.start_timestamp
        else:
            start_timestamp = (
                video_clip.start_timestamp
                if start_timestamp > video_clip.start_timestamp
                else start_timestamp
            )

        if end_timestamp is None:
            end_timestamp = video_clip.end_timestamp
        else:
            end_timestamp = (
                video_clip.end_timestamp
                if end_timestamp < video_clip.end_timestamp
                else end_timestamp
            )

    if total_clips == 0:
        print(f"{get_current_timestamp()}\t\tError: No valid clips to merge found.")
        return True

    # Write out the video files file
    ffmpeg_join_filehandle, ffmpeg_join_filename = mkstemp(suffix=".txt", text=True)
    with os.fdopen(ffmpeg_join_filehandle, "w") as fp:
        fp.write(file_content)

    _LOGGER.debug("Video file contains:\n%s", file_content)
    # Write out the meta data file.
    meta_content = ";FFMETADATA1" + os.linesep + meta_content

    ffmpeg_meta_filehandle, ffmpeg_meta_filename = mkstemp(suffix=".txt", text=True)
    with os.fdopen(ffmpeg_meta_filehandle, "w") as fp:
        fp.write(meta_content)

    _LOGGER.debug("Meta file contains:\n%s", meta_content)

    ffmpeg_params = [
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        ffmpeg_join_filename,
        "-i",
        ffmpeg_meta_filename,
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
    ]
    if video_settings["movflags_faststart"]:
        ffmpeg_params = ffmpeg_params + ["-movflags", "+faststart"]

    ffmpeg_params = ffmpeg_params + ["-c", "copy"]
    user_timestamp_format = video_settings["timestamp_format"]
    if len(event_info) == 1:
        title_timestamp = (
            event_info[0]
            .metadata["event_timestamp"]
            .astimezone(get_localzone())
            .strftime(user_timestamp_format)
            if event_info[0].metadata["reason"] == "SENTRY"
            else start_timestamp.astimezone(get_localzone()).strftime(
                user_timestamp_format
            )
        )
        title = (
            f"{event_info[0].metadata.get('reason')}: {title_timestamp}"
            if event_info[0].metadata.get("reason") is not None
            else title_timestamp
        )
    else:
        title = (
            f"{start_timestamp.astimezone(get_localzone()).strftime(user_timestamp_format)} - "
            f"{end_timestamp.astimezone(get_localzone()).strftime(user_timestamp_format)}"
        )

    ffmpeg_metadata = [
        "-metadata",
        f"creation_time={start_timestamp.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000000Z')}",
        "-metadata",
        f"description=Created by tesla_dashcam {VERSION_STR}",
        "-metadata",
        f"title={title}",
    ]

    # Go through the events and add the 1st valid coordinations for location to metadata
    for event in event_info:
        try:
            lon = float(event_info[0].metadata["longitude"])
            lat = float(event_info[0].metadata["latitude"])
        except:
            pass
        else:
            # Sometimes event info has a very small (i.e. 2.35754e-311) or 0 value, we ignore if both are 0.
            # 0,0 is in the ocean near Africa.
            if round(lon, 5) == 0 and round(lat, 5) == 0:
                _LOGGER.debug(
                    f"Skipping as longitude {lon} and/or latidude {lat} are invalid."
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

    ffmpeg_command = (
        [video_settings["ffmpeg_exec"]]
        + ["-loglevel", "info"]
        + ffmpeg_params
        + ffmpeg_metadata
        + ["-y", movie_filename]
    )

    _LOGGER.debug(f"FFMPEG Command: {ffmpeg_command}")
    try:
        ffmpeg_output = run(
            ffmpeg_command, capture_output=True, check=True, universal_newlines=True
        )
    except CalledProcessError as exc:
        print(
            f"{get_current_timestamp()}\t\t\tError trying to create movie {movie_filename}. RC: {exc.returncode}\n"
            f"{get_current_timestamp()}\t\t\tCommand: {exc.cmd}\n"
            f"{get_current_timestamp()}\t\t\tError: {exc.stderr}\n\n"
        )
    else:
        _LOGGER.debug("FFMPEG output:\n %s", ffmpeg_output.stdout)
        _LOGGER.debug("FFMPEG error output:\n %s", ffmpeg_output.stderr)
        # Get actual duration of our new video, required for chapters when concatenating.
        metadata = get_metadata(video_settings["ffmpeg_exec"], [movie_filename])
        movie.duration = metadata[0]["duration"] if metadata else None
        movie.filename = movie_filename
        movie.start_timestamp = start_timestamp
        movie.end_timestamp = end_timestamp

        # Set the file timestamp if to be set based on timestamp event
        if video_settings["set_moviefile_timestamp"] != "RENDER":
            moviefile_timestamp = start_timestamp.astimezone(get_localzone())
            if video_settings["set_moviefile_timestamp"] == "STOP":
                moviefile_timestamp = end_timestamp.astimezone(get_localzone())
            elif (
                video_settings["set_moviefile_timestamp"] == "SENTRY"
                and len(event_info) == 1
                and event_info[0].metadata.get("timestamp") is not None
            ):
                moviefile_timestamp = (
                    event_info[0].metadata.get("timestamp").astimezone(get_localzone())
                )

            _LOGGER.debug(
                f"Setting timestamp for movie file {movie_filename} to "
                f"{moviefile_timestamp.strftime('%Y-%m-%dT%H-%M-%S')}"
            )
            moviefile_timestamp = mktime(moviefile_timestamp.timetuple())
            os.utime(movie_filename, (moviefile_timestamp, moviefile_timestamp))

    # Remove temp join file.
    # noinspection PyBroadException,PyPep8
    try:
        os.remove(ffmpeg_join_filename)
    except:
        _LOGGER.debug(f"Failed to remove {ffmpeg_join_filename}")
        pass

    # Remove temp join file.
    # noinspection PyBroadException,PyPep8
    try:
        os.remove(ffmpeg_meta_filename)
    except:
        _LOGGER.debug(f"Failed to remove {ffmpeg_meta_filename}")
        pass

    # Remove image video
    if title_video_filename:
        # noinspection PyBroadException,PyPep8
        try:
            os.remove(title_video_filename)
        except:
            _LOGGER.debug(f"Failed to remove {title_video_filename}")
            pass

    if movie.filename is None:
        return False

    return True


def make_folder(parameter, folder):
    # Create folder if not already existing.
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        print(
            f"{get_current_timestamp()}Error creating folder {folder} for parameter {parameter}"
        )
        return False

    return True


def delete_intermediate(movie_files):
    """ Delete the files provided in list """
    for file in movie_files:
        if file is not None:
            if os.path.isfile(file):
                _LOGGER.debug(f"Deleting file {file}.")
                try:
                    os.remove(file)
                except OSError as exc:
                    print(
                        f"{get_current_timestamp()}\t\tError trying to remove file {file}: {exc}"
                    )
            elif os.path.isdir(file):
                _LOGGER.debug(f"Deleting folder {file}.")
                # This is more specific for Mac but won't hurt on other platforms.
                if os.path.exists(os.path.join(file, ".DS_Store")):
                    # noinspection PyBroadException,PyPep8
                    try:
                        os.remove(os.path.join(file, ".DS_Store"))
                    except:
                        _LOGGER.debug(f"Failed to remove .DS_Store from {file}")
                        pass

                try:

                    os.rmdir(file)
                except OSError as exc:
                    print(
                        f"{get_current_timestamp()}\t\tError trying to remove folder {file}: {exc}"
                    )


def process_folders(source_folders, video_settings, delete_source):
    """ Process all clips found within folders. """

    # Retrieve all the video files within the folders provided.
    event_list = get_movie_files(source_folders, video_settings)

    if event_list is None:
        print(f"{get_current_timestamp()}No video files found to process.")
        return

    start_time = timestamp()

    total_clips = 0
    for _, (event_folder, event_info) in enumerate(event_list.items()):
        total_clips = total_clips + event_info.count
    print(
        f"{get_current_timestamp()}There are {len(event_list)} event folder(s) with {total_clips} clips to process."
    )

    # Loop through all the events (folders) sorted.
    movies = {}
    merge_group_template = video_settings["merge_group_template"]
    timestamp_format = video_settings["merge_timestamp_format"]

    for event_count, event_folder in enumerate(sorted(event_list)):
        event_info = event_list.get(event_folder)

        # Get the start and ending timestamps, we add duration to
        # last timestamp to get true ending.
        first_clip_tmstp = event_info.start_timestamp
        last_clip_tmstp = event_info.end_timestamp

        # Skip this folder if we it does not fall within provided timestamps.
        if (
            video_settings["start_timestamp"] is not None
            and last_clip_tmstp < video_settings["start_timestamp"]
        ):
            # Clips from this folder are from before start timestamp requested.
            _LOGGER.debug(
                f"Clips in folder end at {last_clip_tmstp.astimezone(get_localzone())} which is still before "
                f'start timestamp {video_settings["start_timestamp"]}'
            )
            continue

        if (
            video_settings["end_timestamp"] is not None
            and first_clip_tmstp > video_settings["end_timestamp"]
        ):
            # Clips from this folder are from after end timestamp requested.
            _LOGGER.debug(
                f"Clips in folder start at {first_clip_tmstp.astimezone(get_localzone())} which is after "
                f'end timestamp {video_settings["end_timestamp"]}'
            )
            continue

        # No processing, add to list of movies to merge if what was provided is just a file
        if event_info.isfile:
            key = event_info.template(
                merge_group_template, timestamp_format, video_settings
            )
            if movies.get(key) is None:
                movies.update({key: Movie()})

            movies.get(key).set_event(event_info)
            continue

        # Determine the starting and ending timestamps for the clips in this folder based on start/end timestamps
        # provided and offsets.
        # If set for Sentry then offset is only used for clips with reason Sentry and having a event timestamp.
        event_start_timestamp = first_clip_tmstp
        event_end_timestamp = last_clip_tmstp
        if video_settings["sentry_offset"]:
            if (
                event_info.metadata["reason"] == "SENTRY"
                and event_info.metadata["event_timestamp"] is not None
            ):
                if video_settings["start_offset"] is not None:
                    # Recording reason is for Sentry so will use the event timestamp.
                    event_start_timestamp = event_info.metadata[
                        "event_timestamp"
                    ] + timedelta(seconds=video_settings["start_offset"])
                    # make sure that we do not end up at an earlier timestamp then what the clip itself is.
                    _LOGGER.debug(
                        f"Clip starting timestamp changed to "
                        f"{event_start_timestamp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} "
                        f"from {first_clip_tmstp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} "
                        f"due to Sentry event and start offset off {video_settings['start_offset']}"
                    )

                # If end offset is 0 then it means don't cut it short.
                if video_settings["end_offset"] is not None:
                    event_end_timestamp = event_info.metadata[
                        "event_timestamp"
                    ] + timedelta(seconds=video_settings["end_offset"])
                    _LOGGER.debug(
                        f"Clip end timestamp changed to "
                        f"{event_end_timestamp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')}"
                        f" from {last_clip_tmstp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} "
                        f"due to Sentry event and end offset off {video_settings['end_offset']}"
                    )
        else:
            if video_settings["start_offset"] is not None:
                # Not using Sentry timestamp but just offset based on clips instead.
                event_start_timestamp = first_clip_tmstp + timedelta(
                    seconds=abs(video_settings["start_offset"])
                )
                _LOGGER.debug(
                    f"Clip starting timestamp changed to "
                    f"{event_start_timestamp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} from "
                    f"{first_clip_tmstp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} due to "
                    f"start offset off {video_settings['start_offset']}"
                )

            if video_settings["end_offset"] is not None:
                # Figure out potential end timestamp for clip based on offset and end timestamp.
                event_end_timestamp = last_clip_tmstp - timedelta(
                    seconds=abs(video_settings["end_offset"])
                )
                _LOGGER.debug(
                    f"Clip end timestamp changed to "
                    f"{event_end_timestamp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} from "
                    f"{last_clip_tmstp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} due to "
                    f"end offset off {video_settings['end_offset']}"
                )

        if event_start_timestamp < first_clip_tmstp:
            event_start_timestamp = first_clip_tmstp
            _LOGGER.debug(
                f"Clip start timestamp changed back to "
                f"{first_clip_tmstp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} as "
                f"updated offset timestamp was before clip start timestamp"
            )

        # make sure that we do not end up at a later timestamp then what the clip itself is.
        if event_end_timestamp > last_clip_tmstp:
            event_end_timestamp = last_clip_tmstp
            _LOGGER.debug(
                f"Clip end timestamp changed back to "
                f"{last_clip_tmstp.astimezone(get_localzone()).strftime('%Y-%m-%dT%H-%M-%S')} as "
                f"updated offset timestamp was after clip end timestamp"
            )

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
                f"{get_current_timestamp()}\tSkipping folder {event_folder} as {event_movie_filename} is already "
                f"created ({event_count + 1}/{len(event_list)})"
            )

            # Get actual duration of our new video, required for chapters when concatenating.
            metadata = get_metadata(
                video_settings["ffmpeg_exec"], [event_movie_filename]
            )
            event_info.duration = metadata[0]["duration"] if metadata else None
            event_info.filename = event_movie_filename
            event_info.start_timestamp = event_start_timestamp
            event_info.end_timestamp = event_end_timestamp
            key = event_info.template(
                merge_group_template, timestamp_format, video_settings
            )
            if movies.get(key) is None:
                movies.update({key: Movie()})

            movies.get(key).set_event(event_info)
            continue

        print(
            f"{get_current_timestamp()}\tProcessing {event_info.count} clips in folder {event_folder} "
            f"({event_count + 1}/{len(event_list)})"
        )

        # Loop through all the clips within the event.
        delete_folder_clips = []
        delete_folder_files = delete_source
        delete_file_list = []

        for clip_number, clip_timestamp in enumerate(event_info.sorted):
            clip_info = event_info.clip(clip_timestamp)

            if create_intermediate_movie(
                event_info,
                clip_info,
                (event_start_timestamp, event_end_timestamp),
                video_settings,
                clip_number,
            ):

                if clip_info.filename != event_info.filename:
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
            f"{get_current_timestamp()}\t\tCreating movie {event_movie_filename}, please be patient."
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
                if movies.get(key) is None:
                    movies.update({key: Movie()})

                movies.get(key).set_event(event_info)

                print(
                    f"{get_current_timestamp()}\tMovie {event_info.filename} for folder {event_folder} with "
                    f"duration {str(timedelta(seconds=int(event_info.duration)))} is ready."
                )

                # Delete the intermediate files we created.
                if not video_settings["keep_intermediate"]:
                    _LOGGER.debug(
                        f"Deleting {len(delete_folder_clips)} intermediate files"
                    )
                    delete_intermediate(delete_folder_clips)
        else:
            delete_folder_files = False

        # Delete the source files if stated to delete.
        # We only do so if there were no issues in processing the clips
        if delete_folder_files:
            print(
                f"{get_current_timestamp()}\t\tDeleting {len(delete_file_list) + 2} files and folder {event_folder}"
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
    # We only do this if merge is enabled OR if we only have 1 movie with 1 event clip and for
    # output a specific filename was provided not matching the filename for the event clip
    movies_list = None
    if movies:
        if video_settings["merge_subdirs"] or (
            video_settings["target_filename"] is not None
            and len(movies) == 1
            and len(list(movies.values())[0].items) == 1
            and list(movies.values())[0].first_item.filename
            != os.path.join(
                video_settings["target_folder"], video_settings["target_filename"]
            )
        ):
            movies_list = []
            merge_group_template = video_settings["merge_group_template"]
            if merge_group_template is not None or merge_group_template == "":
                _LOGGER.debug(
                    f"Merging video files in groups based on template "
                    f"{merge_group_template}, {len(movies)} will be created."
                )
            elif video_settings["merge_subdirs"]:
                _LOGGER.debug(
                    f"Merging video files into video file "
                    f"{video_settings['movie_filename']}."
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
                    f"{get_current_timestamp()}\tCreating movie {movie_filename}, please be patient."
                )

                # Only set title screen map if requested and # of events for this movie is greater then 1
                title_screen_map = (
                    video_settings["video_layout"].title_screen_map
                    and movies.get(movie).count > 1
                )

                if create_movie(
                    movies.get(movie),
                    movies.get(movie).items_sorted,
                    movie_filename,
                    video_settings,
                    video_settings["chapter_offset"],
                    title_screen_map,
                ):

                    if movies.get(movie).filename is not None:
                        movies_list.append(
                            (
                                movies.get(movie).filename,
                                str(timedelta(seconds=int(movies.get(movie).duration))),
                            )
                        )

                        # Delete the 1 event movie if we created the movie because there was only 1 folder.
                        if not video_settings["merge_subdirs"]:
                            _LOGGER.debug(
                                f"Deleting "
                                f"{list(movies.values())[0].first_item.filename} event file"
                            )
                            delete_intermediate(
                                [list(movies.values())[0].first_item.filename]
                            )
                        elif not video_settings["keep_events"]:
                            # Delete the event files now.
                            delete_file_list = []
                            for _, event_info in movies.get(movie).items:
                                delete_file_list.append(event_info.filename)
                            _LOGGER.debug(
                                f"Deleting {len(delete_file_list)} event files"
                            )
                            delete_intermediate(delete_file_list)
        else:
            print(
                f"{get_current_timestamp()}All folders have been processed, resulting movie files are located in "
                f"{video_settings['target_folder']}"
            )
    else:
        print(f"{get_current_timestamp()}No clips found.")

    end_time = timestamp()
    print(
        f"{get_current_timestamp()}Total processing time: {str(timedelta(seconds=int((end_time - start_time))))}"
    )
    if video_settings["notification"]:
        if movies_list is None:
            # No merging of movies occurred.
            message = (
                "{total_folders} folder{folders} with {total_clips} clip{clips} have been processed, "
                "{target_folder} contains resulting files.".format(
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
                    f"{get_current_timestamp()} Movie {movies_list[0][0]} with duration {movies_list[0][0]} "
                    f"has been created."
                )

            else:
                # Multiple movies were created, listing them all out.
                print(f"{get_current_timestamp()} Following movies have been created:")
                for movie_entry in movies_list:
                    print(
                        f"{get_current_timestamp()}\t{movie_entry[0]} with duration {movie_entry[1]}"
                    )

            if len(movies) == len(movies_list):
                # Number of movies created matches how many we should have created.
                message = (
                    "{total_folders} folder{folders} with {total_clips} clip{clips} have been processed, "
                    "{total_movies} movie {movies} been created.".format(
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
                    "{total_folders} folder{folders} with {total_clips} clip{clips} have been processed, "
                    "{total_movies} {movies} been created out of {all_movies}.".format(
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
    """ Return absolute path for provided relative item based on location

    of program.
    """
    # If compiled with pyinstaller then sys._MEIPASS points to the location
    # of the bundle. Otherwise path of python script is used.
    base_path = getattr(sys, "_MEIPASS", str(Path(__file__).parent))
    return os.path.join(base_path, relative_path)


def notify_macos(title, subtitle, message):
    """ Notification on MacOS """
    try:
        run(
            [
                "osascript",
                '-e display notification "{message}" with title "{title}" '
                'subtitle "{subtitle}"'
                "".format(message=message, title=title, subtitle=subtitle),
            ]
        )
    except Exception as exc:
        print(f"{get_current_timestamp()}Failed in notifification: {str(exc)}")


def notify_windows(title, subtitle, message):
    """ Notification on Windows """

    # Section commented out, waiting to see if it really does not work on Windows 7
    # This works only on Windows 10 9r Windows Server 2016/2019. Skipping for everything else
    #    from platform import win32_ver
    #    if win32_ver()[0] != 10:
    #        return
    global TOASTER_INSTANCE

    # noinspection PyBroadException
    try:
        # noinspection PyUnresolvedReferences,PyPackageRequirements
        from win10toast import ToastNotifier

        if TOASTER_INSTANCE is None:
            TOASTER_INSTANCE = ToastNotifier()

        TOASTER_INSTANCE.show_toast(
            threaded=True,
            title=f"{title} {subtitle}",
            msg=message,
            duration=5,
            icon_path=resource_path("tesla_dashcam.ico"),
        )

        run(["notify-send", f'"{title} {subtitle}"', f'"{message}"'])
    except Exception:
        pass


def notify_linux(title, subtitle, message):
    """ Notification on Linux """
    try:
        run(["notify-send", f'"{title} {subtitle}"', f'"{message}"'])
    except Exception as exc:
        print(f"{get_current_timestamp()}Failed in notifification: {str(exc)}")


def notify(title, subtitle, message):
    """ Call function to send notification based on OS """
    if PLATFORM == "darwin":
        notify_macos(title, subtitle, message)
    elif PLATFORM == "win32":
        notify_windows(title, subtitle, message)
    elif PLATFORM == "linux":
        notify_linux(title, subtitle, message)


def main() -> int:
    """ Main function """

    loglevels = dict(
        (logging.getLevelName(level), level) for level in [10, 20, 30, 40, 50]
    )

    movie_folder = os.path.join(str(Path.home()), MOVIE_HOMEDIR.get(PLATFORM), "")

    global display_ts

    # Check if ffmpeg exist, if not then hope it is in default path or
    # provided.
    internal_ffmpeg = getattr(sys, "frozen", None) is not None
    ffmpeg_default = resource_path(FFMPEG.get(PLATFORM, "ffmpeg"))

    if not os.path.isfile(ffmpeg_default):
        internal_ffmpeg = False
        ffmpeg_default = FFMPEG.get(PLATFORM, "ffmpeg")

    epilog = (
        "This program leverages ffmpeg which is included. See https://ffmpeg.org/ for more information on ffmpeg"
        if internal_ffmpeg
        else "This program requires ffmpeg which can be downloaded from: https://ffmpeg.org/download.html"
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
        help="Folder(s) (events) containing the saved camera files. Filenames can be provided as well to manage "
        "individual clips.",
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
        "--temp_dir", required=False, type=str, help="R|Path to store temporary files."
    )
    parser.add_argument(
        "--no-notification",
        dest="system_notification",
        action="store_false",
        help="Do not create a notification upon " "completion.",
    )

    parser.add_argument(
        "--display_ts",
        action="store_true",
        help="Display timestamps on tesla_dashcam text output. DOES NOT AFFECT VIDEO OUTPUT.",
    )

    input_group = parser.add_argument_group(
        title="Video Input",
        description="Options related to what clips and events to process.",
    )
    input_group.add_argument(
        "--skip_existing",
        dest="skip_existing",
        action="store_true",
        help="Skip creating encoded video file if it already exist. Note that only existence is checked, not if "
        "layout etc. are the same.",
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
        description="Parameters for monitoring of insertion of TeslaCam drive, folder, or file existence.",
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
        help="Enable monitoring and exit once drive with TeslaCam folder has been attached and files processed.",
    )
    monitor_group.add_argument(
        "--monitor_trigger",
        required=False,
        type=str,
        help="Trigger file to look for instead of waiting for drive to be attached. Once file is discovered then "
        "processing will start, file will be deleted when processing has been completed. If source is not "
        "provided then folder where file is located will be used as source.",
    )

    layout_group = parser.add_argument_group(
        title="Video Layout",
        description="Set what the layout of the resulting video should be",
    )
    layout_group.add_argument(
        "--layout",
        required=False,
        choices=["WIDESCREEN", "FULLSCREEN", "PERSPECTIVE", "CROSS", "DIAMOND"],
        default="FULLSCREEN",
        type=str.upper,
        help="R|Layout of the created video.\n"
        "    FULLSCREEN: Front camera center top, "
        "side cameras underneath it with rear camera between side camera.\n"
        "    WIDESCREEN: Front camera on top with side and rear cameras smaller underneath it.\n"
        "    PERSPECTIVE: Similar to FULLSCREEN but then with side cameras in perspective.\n"
        "    CROSS: Front camera center top, side cameras underneath, and rear camera center bottom.\n"
        "    DIAMOND: Front camera center top, side cameras below front camera left and right of front, "
        "and rear camera center bottom.\n",
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
        help="R|Set camera clip scale for all clips, scale of 1 is 1280x960 camera clip.\n"
        "If provided with value then it is default for all cameras, to set the scale for a specific "
        "camera provide camera=<front, left, right,rear> <scale>\n"
        "for example:\n"
        "  --scale 0.5                                             all are 640x480\n"
        "  --scale 640x480                                         all are 640x480\n"
        "  --scale 0.5 --scale camera=front 1                      all are 640x480 except front at 1280x960\n"
        "  --scale camera=left .25 --scale camera=right 320x240    left and right are set to 320x240\n"
        "Defaults:\n"
        "    WIDESCREEN: 1/2 (front 1280x960, others 640x480, video is 1920x1920)\n"
        "    FULLSCREEN: 1/2 (640x480, video is 1920x960)\n"
        "    CROSS: 1/2 (640x480, video is 1280x1440)\n"
        "    DIAMOND: 1/2 (640x480, video is 1920x976)\n",
    )
    layout_group.add_argument(
        "--mirror",
        dest="rear_or_mirror",
        action="store_const",
        const=1,
        help="Video from side and rear cameras as if being viewed through the mirror. Default when not providing "
        "parameter --no-front. Cannot be used in combination with --rear.",
    )
    layout_group.add_argument(
        "--rear",
        dest="rear_or_mirror",
        action="store_const",
        const=0,
        help="Video from side and rear cameras as if looking backwards. Default when providing parameter --no-front. "
        "Cannot be used in combination with --mirror.",
    )
    layout_group.add_argument(
        "--swap",
        dest="swap_leftright",
        action="store_const",
        const=1,
        help="Swap left and right cameras in output, default when side and rear cameras are as if looking backwards. "
        "See --rear parameter.",
    )
    layout_group.add_argument(
        "--no-swap",
        dest="swap_leftright",
        action="store_const",
        const=0,
        help="Do not swap left and right cameras, default when side and rear cameras are as if looking through a "
        "mirror. Also see --mirror parameter",
    )
    layout_group.add_argument(
        "--swap_frontrear",
        dest="swap_frontrear",
        action="store_true",
        help="Swap front and rear cameras in output.",
    )
    layout_group.add_argument(
        "--background",
        dest="background",
        default="black",
        type=str.lower,
        help="Background color for video. Can be a color string or RGB value. Also see --fontcolor.",
    )

    layout_group.add_argument(
        "--title_screen_map",
        dest="title_screen_map",
        action="store_true",
        help="Show a map of the event location for the first 3 seconds of the event movie, when merging events it will also create map with lines linking the events",
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
        help="Font size for timestamp. Default is scaled based on resulting video size.",
    )
    text_overlay_group.add_argument(
        "--fontcolor",
        required=False,
        type=str.lower,
        default="white",
        help="R|Font color for timestamp. Any color is accepted as a color string or RGB value.\n"
        "Some potential values are:\n"
        "    white\n"
        "    yellowgreen\n"
        "    yellowgreen@0.9\n"
        "    Red\n:"
        "    0x2E8B57\n"
        "For more information on this see ffmpeg documentation for color: https://ffmpeg.org/ffmpeg-utils.html#Color",
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
        "    {event_timestamp_countdown_rolling} - Local time which continuously updates "
        "(shorthand for '%%{{hms:localtime:{event_timestamp}}}'), string\n"
        "    {event_city} - City name from events.json (if provided), string\n"
        "    {event_reason} - Recording reason from events.json (if provided), string\n"
        "    {event_latitude} - Estimated latitude from events.json (if provided), float\n"
        "    {event_longitude} - Estimated longitude from events.json (if provided), float\n"
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
        "Determines how timestamps should be represented. Any valid value from strftime is accepted."
        "Default is set '%%x %%X' which is locale's appropriate date and time representation"
        "More info: https://strftime.org",
    )

    filter_group = parser.add_argument_group(
        title="Timestamp Restriction",
        description="Restrict video to be between start and/or end timestamps. Timestamp to be provided in a ISO-8601 "
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
        help="Skip x number of seconds from start of event for resulting video. Default is 0 seconds, 60 seconds if "
        "--sentry_offset is provided.",
    )
    offset_group.add_argument(
        "--end_offset",
        dest="end_offset",
        type=int,
        help="Ignore the last x seconds of the event for resulting video. Default is 0 seconds, 30 seconds if "
        "--sentry_offset is provided.",
    )

    offset_group.add_argument(
        "--sentry_offset",
        dest="sentry_offset",
        action="store_true",
        help="start_offset and end_offset will be based on when timestamp of object detection occurred for Sentry"
        "events instead of start/end of event.",
    )

    output_group = parser.add_argument_group(
        title="Video Output", description="Options related to resulting video creation."
    )
    output_group.add_argument(
        "--output",
        required=False,
        default=movie_folder,
        type=str,
        help="R|Path/Filename for the new movie file. Event files will be stored in same folder."
        + os.linesep,
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
        help="Slow down video output. Accepts a number that is then used as multiplier, providing 2 means half the "
        "speed.",
    )
    output_group.add_argument(
        "--speedup",
        dest="speed_up",
        type=float,
        default=argparse.SUPPRESS,
        help="Speed up the video. Accepts a number that is then used as a multiplier, providing 2 means "
        "twice the speed.",
    )
    output_group.add_argument(
        "--chapter_offset",
        dest="chapter_offset",
        type=int,
        default=0,
        help="Offset in seconds for chapters in merged video. Negative offset is # of seconds before the end of the "
        "subdir video, positive offset if # of seconds after the start of the subdir video.",
    )

    output_group.add_argument(
        "--merge",
        required=False,
        dest="merge_group_template",
        type=str,
        nargs="?",
        const="",
        default=argparse.SUPPRESS,
        help="R|Merge the video files from different folders (events) into 1 big video file.\n"
        "Optionally add a template string to group events in different video files based on the template.\n"
        "Valid format variables:\n"
        "    {layout} - Layout of the created movie (see --layout)\n"
        "    {start_timestamp} - Local time the event started at\n"
        "    {end_timestamp} - Local time the event ends at\n"
        "    {event_timestamp} - Timestamp from events.json (if provided), string\n"
        "    {event_city} - City name from events.json (if provided), string\n"
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
        "Determines how timestamps should be represented within merge_template. Any valid value from strftime is accepted."
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
        help="Do not remove the event video files that are created when merging events into a video file (see --merge)",
    )

    output_group.add_argument(
        "--set_moviefile_timestamp",
        dest="set_moviefile_timestamp",
        required=False,
        choices=["START", "STOP", "SENTRY", "RENDER"],
        type=str.upper,
        default="START",
        help="Match modification timestamp of resulting video files to event timestamp. Use START to match with when "
        "the event started, STOP for end time of the event, SENTRY for Sentry event timestamp, or RENDER to not change it.",
    )

    advancedencoding_group = parser.add_argument_group(
        title="Advanced encoding settings", description="Advanced options for encoding"
    )

    if PLATFORM == "darwin":
        if PROCESSOR != "arm":
            nogpuhelp = "R|Disable use of GPU acceleration, default is to use GPU acceleration.\n"
            gpuhelp = "R|Use GPU acceleration (this is the default).\n"
        else:
            nogpuhelp = "R|Disable use of GPU acceleration, this is the default as currently ffmpeg has issues on Apple Silicon with GPU acceleration.\n"
            gpuhelp = (
                "R|Use GPU acceleration.\n"
                "  Note: ffmpeg currently seems to have issues on Apple Silicon with GPU acceleration resulting in corrupt video.\n"
            )

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
            choices=["nvidia", "intel", "rpi"],
            type=str.lower,
            help="Type of graphics card (GPU) in the system. This determines the encoder that will be used."
            "This parameter is mandatory if --gpu is provided.",
        )

    advancedencoding_group.add_argument(
        "--no-faststart",
        dest="faststart",
        action="store_true",
        help="Do not enable flag faststart on the resulting video files. Use this when using a network share and "
        "errors occur during encoding.",
    )

    advancedencoding_group.add_argument(
        "--quality",
        required=False,
        choices=["LOWEST", "LOWER", "LOW", "MEDIUM", "HIGH"],
        default="LOWER",
        type=str.upper,
        help="Define the quality setting for the video, higher quality means bigger file size but might "
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
        help="Speed to optimize video. Faster speed results in a bigger file. This does not impact the quality of "
        "the video, just how much time is used to compress it.",
    )

    advancedencoding_group.add_argument(
        "--fps",
        required=False,
        type=int,
        default=24,
        help="Frames per second for resulting video. Tesla records at about 33fps hence going higher wouldn't do "
        "much as frames would just be duplicated. Default is 24fps which is the standard for movies and TV shows",
    )

    if internal_ffmpeg:
        advancedencoding_group.add_argument(
            "--ffmpeg",
            required=False,
            type=str,
            default=argparse.SUPPRESS,
            help="Full path and filename for alternative " "ffmpeg.",
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
        "    x264: standard encoding, can be viewed on most devices but results in bigger file.\n"
        "    x265: newer encoding standard but not all devices support this yet.\n",
    )
    advancedencoding_group.add_argument(
        "--enc",
        required=False,
        type=str,
        default=argparse.SUPPRESS,
        help="R|Provide a custom encoder for video creation. Cannot be used in combination with --encoding.\n"
        "Note: when using this option the --gpu option is ignored. To use GPU hardware acceleration specify an "
        "encoding that provides this.",
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
        help="A check for new updates is performed every time. With this parameter that can be disabled",
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

    _LOGGER.debug(f"Arguments : {args}")
    _LOGGER.debug(f"Platform is {PLATFORM}")
    _LOGGER.debug(f"Processor is {PROCESSOR}")

    # Check that any mutual exclusive items are not both provided.
    if "speed_up" in args and "slow_down" in args:
        print(
            f"{get_current_timestamp()}Option --speed_up and option --slow_down cannot be used together, "
            f"only use one of them."
        )
        return 1

    if "enc" in args and "encoding" in args:
        print(
            f"{get_current_timestamp()}Option --enc and option --encoding cannot be used together, "
            f"only use one of them."
        )
        return 1

    if not args.no_check_for_updates or args.check_for_updates:
        release_info = check_latest_release(args.include_beta)
        if release_info is not None:
            new_version = False
            if release_info.get("tag_name") is not None:
                github_version = release_info.get("tag_name").split(".")
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
                            f"New {beta}release {release_info.get('tag_name')} is available. You are on version "
                            f"{VERSION_STR}",
                        )
                    release_notes = (
                        "Use --check_for_update to get latest " "release notes."
                    )

                print(
                    f"{get_current_timestamp()}New {beta}release {release_info.get('tag_name')} is available for "
                    f"download ({release_info.get('html_url')}). You are currently on {VERSION_STR}. {release_notes}"
                )

                if args.check_for_updates:
                    print(
                        f"{get_current_timestamp()}You can download the new release from: "
                        f"{release_info.get('html_url')}"
                    )
                    print(
                        f"{get_current_timestamp()}Release Notes:\n {release_info.get('body')}"
                    )
                    return 0
            else:
                if args.check_for_updates:
                    print(
                        f"{get_current_timestamp()}{VERSION_STR} is the latest release available."
                    )
                    return 0
        else:
            print(f"{get_current_timestamp()} Did not retrieve latest version info.")

    internal_ffmpeg = getattr(args, "ffmpeg", None) is None and internal_ffmpeg
    ffmpeg = getattr(args, "ffmpeg", ffmpeg_default) or ""
    if not internal_ffmpeg and (ffmpeg == "" or which(ffmpeg) is None):
        print(
            f"{get_current_timestamp()}ffmpeg is a requirement, unable to find {ffmpeg} executable. Please ensure it exist and is located "
            f"within PATH environment or provide full path using parameter --ffmpeg."
        )
        return 1

    if internal_ffmpeg and PLATFORM == "darwin" and PROCESSOR == "arm":
        print(
            "Internal ffmpeg version is used which has been compiled for Intel Macs. Better results in both "
            "performance and size can be achieved by downloading an Apple Silicon compiled ffmpeg from: https://www.osxexperts.net "
            "and providing it leveraging the --ffmpeg parameter."
        )

    if args.layout == "PERSPECTIVE":
        layout_settings = FullScreen()
        layout_settings.perspective = True
    else:
        if args.layout == "WIDESCREEN":
            layout_settings = WideScreen()
        elif args.layout == "FULLSCREEN":
            layout_settings = FullScreen()
        elif args.layout == "CROSS":
            layout_settings = Cross()
        elif args.layout == "DIAMOND":
            layout_settings = Diamond()
        else:
            layout_settings = FullScreen()

        layout_settings.perspective = args.perspective

    layout_settings.cameras("Front").include = not args.no_front
    layout_settings.cameras("Left").include = not args.no_left
    layout_settings.cameras("Right").include = not args.no_right
    layout_settings.cameras("Rear").include = not args.no_rear

    # Check if either rear or mirror argument has been provided.
    # If front camera then default to mirror, if no front camera then default to rear.
    side_camera_as_mirror = (
        layout_settings.cameras("Front").include
        if args.rear_or_mirror is None
        else args.rear_or_mirror
    )
    mirror_sides = ", hflip" if side_camera_as_mirror else ""

    # For scale first set the main clip one if provided, this than allows camera specific ones to override for
    # that camera.
    scaling = parser.args_to_dict(args.clip_scale, "scale")
    main_scale = search_dict(None, "camera", scaling)

    if main_scale is not None:
        layout_settings.scale = main_scale.get("scale", layout_settings.scale)

    for scale in scaling:
        if scale.get("camera", "").lower() in ["front", "left", "right", "rear"]:
            camera_scale = scale.get("scale")
            if camera_scale is not None:
                layout_settings.cameras(
                    scale["camera"].lower().capitalize()
                ).scale = camera_scale

    layout_settings.font.halign = (
        args.halign if args.halign is not None else layout_settings.font.halign
    )
    layout_settings.font.valign = (
        args.valign if args.valign is not None else layout_settings.font.valign
    )

    # Determine if left and right cameras should be swapped or not.
    # No more arguments related to cameras (i.e .scale, include or not) can be processed from now on.
    # Up till now Left means left camera and Right means Right camera.
    # From this point forward Left can mean Right camera if we're swapping output.
    layout_settings.swap_left_right = (
        not side_camera_as_mirror
        if args.swap_leftright is None
        else args.swap_leftright
    )

    layout_settings.swap_front_rear = args.swap_frontrear
    layout_settings.title_screen_map = args.title_screen_map

    layout_settings.font.font = args.font
    layout_settings.font.color = args.fontcolor
    if args.fontsize is not None and args.fontsize > 0:
        layout_settings.font.size = args.fontsize

    black_base = "color=duration={duration}:"
    black_size = f"s={{width}}x{{height}}:c={args.background}, fps={args.fps} "

    ffmpeg_base = (
        black_base
        + black_size.format(
            width=layout_settings.video_width, height=layout_settings.video_height
        )
        + "[base]"
    )

    ffmpeg_black_video = ";" + black_base + black_size

    input_clip = "base"
    ffmpeg_video_position = ""

    ffmpeg_left_camera = ""
    camera = "Left"
    if layout_settings.cameras(camera).include:
        ffmpeg_left_camera = (
            "setpts=PTS-STARTPTS, "
            "scale={clip_width}x{clip_height} {mirror}{options}"
            " [left]".format(
                clip_width=layout_settings.cameras(camera).width,
                clip_height=layout_settings.cameras(camera).height,
                mirror=mirror_sides,
                options=layout_settings.cameras(camera).options,
            )
        )

        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][left] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [left1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.cameras(camera).xpos,
                y_pos=layout_settings.cameras(camera).ypos,
            )
        )
        input_clip = "left1"

    ffmpeg_front_camera = ""
    camera = "Front"
    if layout_settings.cameras(camera).include:
        ffmpeg_front_camera = (
            "setpts=PTS-STARTPTS, "
            "scale={clip_width}x{clip_height} {options}"
            " [front]".format(
                clip_width=layout_settings.cameras(camera).width,
                clip_height=layout_settings.cameras(camera).height,
                options=layout_settings.cameras(camera).options,
            )
        )
        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][front] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [front1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.cameras(camera).xpos,
                y_pos=layout_settings.cameras(camera).ypos,
            )
        )
        input_clip = "front1"

    ffmpeg_right_camera = ""
    camera = "Right"
    if layout_settings.cameras(camera).include:
        ffmpeg_right_camera = (
            "setpts=PTS-STARTPTS, "
            "scale={clip_width}x{clip_height} {mirror}{options}"
            " [right]".format(
                clip_width=layout_settings.cameras(camera).width,
                clip_height=layout_settings.cameras(camera).height,
                mirror=mirror_sides,
                options=layout_settings.cameras(camera).options,
            )
        )
        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][right] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [right1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.cameras(camera).xpos,
                y_pos=layout_settings.cameras(camera).ypos,
            )
        )
        input_clip = "right1"

    ffmpeg_rear_camera = ""
    camera = "Rear"
    if layout_settings.cameras(camera).include:
        ffmpeg_rear_camera = (
            "setpts=PTS-STARTPTS, "
            # "crop=512:798:225:26, "
            "scale={clip_width}x{clip_height} {mirror}{options}"
            " [rear]".format(
                clip_width=layout_settings.cameras(camera).width,
                clip_height=layout_settings.cameras(camera).height,
                mirror=mirror_sides,
                options=layout_settings.cameras(camera).options,
            )
        )
        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][rear] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [rear1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.cameras(camera).xpos,
                y_pos=layout_settings.cameras(camera).ypos,
            )
        )
        input_clip = "rear1"

    # Text Overlay
    text_overlay_format = (
        args.text_overlay_fmt if args.text_overlay_fmt is not None else None
    )

    # Timestamp format
    timestamp_format = (
        args.timestamp_format if args.timestamp_format is not None else None
    )

    filter_counter = 0
    filter_string = ";[{input_clip}] {filter} [tmp{filter_counter}]"
    ffmpeg_timestamp = ""
    if not args.no_timestamp and text_overlay_format is not None:
        if layout_settings.font.font is None:
            print(
                f"{get_current_timestamp()}Unable to get a font file for platform {PLATFORM}. Please provide valid font file using "
                f"--font or disable timestamp using --no-timestamp."
            )
            return 0

        # noinspection PyPep8
        temp_font_file = (
            f"c:\{layout_settings.font.font}"
            if PLATFORM == "win32"
            else layout_settings.font.font
        )
        if not os.path.isfile(temp_font_file):
            print(
                f"{get_current_timestamp()}Font file {temp_font_file} does not exist. Provide a valid font file using --font or"
                f" disable timestamp using --no-timestamp"
            )
            if PLATFORM == "linux":
                print(
                    f"{get_current_timestamp()}You can also install the fonts using for example: "
                    f"apt-get install ttf-freefont"
                )
            return 0

        # noinspection PyPep8,PyPep8,PyPep8
        ffmpeg_timestamp = (
            ffmpeg_timestamp + f"drawtext=fontfile={layout_settings.font.font}:"
            f"fontcolor={layout_settings.font.color}:fontsize={layout_settings.font.size}:"
            "borderw=2:bordercolor=black@1.0:"
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
            filter=f"mpdecimate=hi=64*48, setpts=N/FRAME_RATE/TB",
            filter_counter=filter_counter,
        )
        input_clip = f"tmp{filter_counter}"
        filter_counter += 1

    ffmpeg_params = ["-preset", args.compression, "-crf", MOVIE_QUALITY[args.quality]]

    use_gpu = (
        getattr(args, "gpu", True)
        if PLATFORM == "darwin" and PROCESSOR != "arm"
        else getattr(args, "gpu", False)
    )

    video_encoding = []
    if not "enc" in args:
        encoding = args.encoding if "encoding" in args else "x264"

        # For x265 add QuickTime compatibility
        if encoding == "x265":
            video_encoding = video_encoding + ["-vtag", "hvc1"]

        # GPU acceleration enabled
        if use_gpu:
            print(f"{get_current_timestamp()}GPU acceleration is enabled")
            if PLATFORM == "darwin":
                video_encoding = video_encoding + ["-allow_sw", "1"]
                encoding = encoding + "_mac"

            else:
                if args.gpu_type is None:
                    print(
                        f"{get_current_timestamp()}Parameter --gpu_type is mandatory when parameter "
                        f"--use_gpu is used."
                    )
                    return 0

                encoding = encoding + "_" + args.gpu_type

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
        display_ts = True

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
            if start_timestamp.tzinfo is None:
                start_timestamp = start_timestamp.astimezone(get_localzone())
        except ValueError as e:
            print(
                f"{get_current_timestamp()}Start timestamp ({args.start_timestamp}) provided is in an incorrect "
                f"format. Parsing error: {str(e)}."
            )
            return 1

    end_timestamp = None
    if args.end_timestamp is not None:
        try:
            end_timestamp = isoparse(args.end_timestamp)
            if end_timestamp.tzinfo is None:
                end_timestamp = end_timestamp.astimezone(get_localzone())
        except ValueError as e:
            print(
                f"{get_current_timestamp()}End timestamp ({args.end_timestamp}) provided is in an incorrect "
                f"format. Parsing error: {str(e)}."
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
        "background": ffmpeg_black_video,
        "ffmpeg_exec": ffmpeg,
        "base": ffmpeg_base,
        "video_layout": layout_settings,
        "clip_positions": ffmpeg_video_position,
        "ffmpeg_text_overlay": ffmpeg_timestamp,
        "text_overlay_format": text_overlay_format,
        "timestamp_format": timestamp_format,
        "ffmpeg_speed": ffmpeg_speed,
        "ffmpeg_motiononly": ffmpeg_motiononly,
        "movflags_faststart": not args.faststart,
        "input_clip": input_clip,
        "other_params": ffmpeg_params,
        "left_camera": ffmpeg_left_camera,
        "front_camera": ffmpeg_front_camera,
        "right_camera": ffmpeg_right_camera,
        "rear_camera": ffmpeg_rear_camera,
        "start_timestamp": start_timestamp,
        "start_offset": 60
        if args.start_offset is None and args.sentry_offset
        else args.start_offset,
        "end_timestamp": end_timestamp,
        "end_offset": 30
        if args.end_offset is None and args.sentry_offset
        else args.end_offset,
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

    _LOGGER.debug(f"Video Settings {video_settings}")
    _LOGGER.debug(f"Layout Settings {layout_settings}")

    # If we constantly run and monitor for drive added or not.
    if video_settings["run_type"] in ["MONITOR", "MONITOR_ONCE"]:

        video_settings.update({"skip_existing": True})

        trigger_exist = False
        if monitor_file is None:
            print(
                f"{get_current_timestamp()}Monitoring for TeslaCam Drive to be inserted. Press CTRL-C to stop"
            )
        else:
            print(
                f"{get_current_timestamp()}Monitoring for trigger {monitor_file} to exist. Press CTRL-C to stop"
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
                                f"{get_current_timestamp()}TeslaCam drive has been ejected."
                            )
                            print(
                                f"{get_current_timestamp()}Monitoring for TeslaCam Drive to be inserted. "
                                f"Press CTRL-C to stop"
                            )

                        sleep(MONITOR_SLEEP_TIME)
                        trigger_exist = False
                        continue

                    # As long as TeslaCam drive is still attached we're going to
                    # keep on waiting.
                    if trigger_exist:
                        _LOGGER.debug(f"TeslaCam Drive still attached")
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
                        _LOGGER.debug(f"Trigger file {monitor_file} does not exist.")
                        sleep(MONITOR_SLEEP_TIME)
                        trigger_exist = False
                        continue

                    if trigger_exist:
                        sleep(MONITOR_SLEEP_TIME)
                        continue

                    message = f"Trigger {monitor_file} exist."
                    trigger_exist = True

                    # Set monitor path, make sure what was provided is a file first otherwise get path.
                    monitor_path = monitor_file
                    if os.path.isfile(monitor_file):
                        monitor_path, _ = os.path.split(monitor_file)

                    # If . is provided then source folder is path where monitor file exist.
                    source_folder_list = []
                    for folder in video_settings["source_folder"]:
                        if folder == ".":
                            source_folder_list.append(monitor_path)
                        else:
                            # If source path provided is absolute then use that for source path
                            if os.path.isabs(folder):
                                source_folder_list.append(folder)
                            else:
                                # Path provided is relative, hence based on path of trigger file.
                                source_folder_list.append(
                                    os.path.join(monitor_path, folder)
                                )

                print(f"{get_current_timestamp()}{message}")
                if args.system_notification:
                    notify("TeslaCam", "Started", message)

                if len(source_folder_list) == 1:
                    print(
                        f"{get_current_timestamp()}Retrieving all files from {source_folder_list[0]}"
                    )
                else:
                    print(f"{get_current_timestamp()}Retrieving all files from: ")
                    for folder in source_folder_list:
                        print(
                            f"{get_current_timestamp()}                          {folder}"
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
                    f"video_settings attribute movie_filename set to {movie_filename}."
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
                                    f"{get_current_timestamp()}Error trying to remove trigger file "
                                    f"{monitor_file}: {exc}"
                                )

                    print(
                        f"{get_current_timestamp()}Exiting monitoring as asked process once."
                    )
                    break

                if monitor_file is None:
                    trigger_exist = True
                    print(
                        f"{get_current_timestamp()}Waiting for TeslaCam Drive to be ejected. Press CTRL-C to stop"
                    )
                else:
                    if os.path.isfile(monitor_file):
                        try:
                            os.remove(monitor_file)
                        except OSError as exc:
                            print(
                                f"{get_current_timestamp()}Error trying to remove trigger file {monitor_file}: {exc}"
                            )
                            break
                        trigger_exist = False

                        print(
                            f"{get_current_timestamp()}Monitoring for trigger {monitor_file}. Press CTRL-C to stop"
                        )
                    else:
                        print(
                            f"{get_current_timestamp()}Waiting for trigger {monitor_file} to be removed. "
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
            f"video_settings attribute movie_filename set to {movie_filename}."
        )
        video_settings.update({"movie_filename": movie_filename})

        process_folders(
            video_settings["source_folder"], video_settings, args.delete_source
        )


if sys.version_info < (3, 8):
    print(
        f"{get_current_timestamp()}Python version 3.8 or higher is required, you have: {sys.version}. Please update your Python version."
    )
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
