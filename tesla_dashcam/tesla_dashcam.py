"""
Merges the 3 Tesla Dashcam and Sentry camera video files into 1 video. If
then further concatenates the files together to make 1 movie.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from fnmatch import fnmatch
from glob import glob
from pathlib import Path
from re import search
from subprocess import CalledProcessError, run
from shutil import which
from tempfile import mkstemp
from time import sleep, time as timestamp

import requests
from psutil import disk_partitions
from tzlocal import get_localzone

# TODO: Move everything into classes and separate files. For example,
#  update class, font class (for timestamp), folder class, clip class (
#  combining front, left, and right info), file class (for individual file).
#  Clip class would then have to merge the camera clips, folder class would
#  have to concatenate the merged clips. Settings class to take in all settings
# TODO: Create kind of logger or output classes for output. That then allows
#  different ones to be created based on where it should go to (stdout,
#  log file, ...).

VERSION = {"major": 0, "minor": 1, "patch": 13, "beta": -1}
VERSION_STR = "v{major}.{minor}.{patch}".format(
    major=VERSION["major"], minor=VERSION["minor"], patch=VERSION["patch"]
)

if VERSION["beta"] > -1:
    VERSION_STR = VERSION_STR + "b{beta}".format(beta=VERSION["beta"])

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
}

MOVIE_HOMEDIR = {
    "darwin": "Movies/Tesla_Dashcam",
    "win32": "Videos\Tesla_Dashcam",
    "cygwin": "Videos/Tesla_Dashcam",
    "linux": "Videos/Tesla_Dashcam",
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
    "x264_RPi": "h264_omx",
    "x265": "libx265",
    "x265_nvidia": "hevc_nvenc",
    "x265_mac": "hevc_videotoolbox",
    "x265_intel": "h265_qsv",
    "x265_RPi": "h265",
}

DEFAULT_FONT = {
    "darwin": "/Library/Fonts/Arial.ttf",
    "win32": "/Windows/Fonts/arial.ttf",
    "cygwin": "/cygdrive/c/Windows/Fonts/arial.ttf",
    "linux": "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
}

HALIGN = {"LEFT": "10", "CENTER": "(w/2-text_w/2)", "RIGHT": "(w-text_w)"}

VALIGN = {"TOP": "10", "MIDDLE": "(h/2-(text_h/2))", "BOTTOM": "(h-(text_h*2))"}

TOASTER_INSTANCE = None


class MovieLayout(object):
    """ Main Layout class
    """

    def __init__(self):
        self._include_front = False
        self._include_left = False
        self._include_right = False
        self._include_rear = False
        self._scale = 0
        self._font_scale = 1
        self._front_width = 0
        self._front_height = 0
        self._left_width = 0
        self._left_height = 0
        self._right_width = 0
        self._right_height = 0
        self._rear_width = 0
        self._rear_height = 0

        self._left_options = ""
        self._front_options = ""
        self._right_options = ""
        self._rear_options = ""

        self._swap_left_right = False

        self._perspective = False

        self._font_halign = HALIGN["CENTER"]
        self._font_valign = VALIGN["BOTTOM"]

    @property
    def front_options(self):
        return self._front_options

    @front_options.setter
    def front_options(self, options):
        self._front_options = options

    @property
    def left_options(self):
        return self._left_options if not self.swap_left_right else self._right_options

    @left_options.setter
    def left_options(self, options):
        self._left_options = options

    @property
    def right_options(self):
        return self._right_options if not self.swap_left_right else self._left_options

    @right_options.setter
    def right_options(self, options):
        self._right_options = options

    @property
    def rear_options(self):
        return self._rear_options

    @rear_options.setter
    def rear_options(self, options):
        self._rear_options = options

    @property
    def swap_left_right(self):
        return self._swap_left_right

    @swap_left_right.setter
    def swap_left_right(self, swap):
        self._swap_left_right = swap

    @property
    def perspective(self):
        return self._perspective

    @perspective.setter
    def perspective(self, new_perspective):
        self._perspective = new_perspective

        if self._perspective:
            self.left_options = (
                ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000, "
                "perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:"
                "x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination"
            )
            self.right_options = (
                ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000,"
                "perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:"
                "x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination"
            )
        else:
            self.left_options = ""
            self.right_options = ""

    @property
    def offset(self):
        return 5 if self.perspective and (self.left or self.right) else 0

    @property
    def front(self):
        return self._include_front

    @front.setter
    def front(self, include):
        self._include_front = include

    @property
    def left(self):
        return self._include_left

    @left.setter
    def left(self, include):
        self._include_left = include

    @property
    def right(self):
        return self._include_right

    @right.setter
    def right(self, include):
        self._include_right = include

    @property
    def rear(self):
        return self._include_rear

    @rear.setter
    def rear(self, include):
        self._include_rear = include

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        self._scale = scale

    @property
    def font_scale(self):
        return self._font_scale

    @font_scale.setter
    def font_scale(self, scale):
        self._font_scale = scale

    @property
    def font_halign(self):
        return self._font_halign

    @font_halign.setter
    def font_halign(self, alignment):
        self._font_halign = HALIGN.get(alignment, self._font_halign)

    @property
    def font_valign(self):
        return self._font_valign

    @font_valign.setter
    def font_valign(self, alignment):
        self._font_valign = VALIGN.get(alignment, self._font_valign)
        print(self._font_valign)

    @property
    def front_width(self):
        return int(self._front_width * self.scale * self.front)

    @front_width.setter
    def front_width(self, size):
        self._front_width = size

    @property
    def front_height(self):
        return int(self._front_height * self.scale * self.front)

    @front_height.setter
    def front_height(self, size):
        self._front_height = size

    @property
    def left_width(self):
        return int(self._left_width * self.scale * self.left)

    @left_width.setter
    def left_width(self, size):
        self._left_width = size

    @property
    def left_height(self):
        return int(self._left_height * self.scale * self.left)

    @left_height.setter
    def left_height(self, size):
        self._left_height = size

    @property
    def right_width(self):
        return int(self._right_width * self.scale * self.right)

    @right_width.setter
    def right_width(self, size):
        self._right_width = size

    @property
    def right_height(self):
        return int(self._right_height * self.scale * self.right)

    @right_height.setter
    def right_height(self, size):
        self._right_height = size

    @property
    def rear_width(self):
        return int(self._rear_width * self.scale * self.rear)

    @rear_width.setter
    def rear_width(self, size):
        self._rear_width = size

    @property
    def rear_height(self):
        return int(self._rear_height * self.scale * self.rear)

    @rear_height.setter
    def rear_height(self, size):
        self._rear_height = size

    @property
    def video_width(self):
        return (
            max(
                self.left_x + self.left_width + self.offset * self.left,
                self.front_x + self.front_width + self.offset * self.front,
                self.right_x + self.right_width + self.offset * self.right,
                self.rear_x + self.rear_width + self.offset * self.rear,
            )
            + self.offset
        )

    @property
    def video_height(self):
        if self.perspective:
            height = int(max(3 / 2 * self.left_height, 3 / 2 * self.right_height))
            height = (
                max(height, self.rear_height) + self.front_height
                if self.rear
                else max(height, self.front_height)
            )
            height = height + 5 if height > 0 else 0
            return height
        else:
            return max(
                self.left_y + self.left_height,
                self.front_y + self.front_height,
                self.right_y + self.right_height,
                self.rear_y + self.rear_height,
            )

    @property
    def front_x(self):
        return self.get_front_xy[0]

    @property
    def front_y(self):
        return self.get_front_xy[1]

    @property
    def get_front_xy(self):
        return (0, 0)

    @property
    def left_x(self):
        return self.get_left_xy[0] if not self.swap_left_right else self.get_right_xy[0]

    @property
    def left_y(self):
        return self.get_left_xy[1] if not self.swap_left_right else self.get_right_xy[1]

    @property
    def get_left_xy(self):
        return (0, 0)

    @property
    def right_x(self):
        return self.get_right_xy[0] if not self.swap_left_right else self.get_left_xy[0]

    @property
    def right_y(self):
        return self.get_right_xy[1] if not self.swap_left_right else self.get_left_xy[1]

    @property
    def get_right_xy(self):
        return (0, 0)

    @property
    def rear_x(self):
        return self.get_rear_xy[0]

    @property
    def rear_y(self):
        return self.get_rear_xy[1]

    @property
    def get_rear_xy(self):
        return (0, 0)


class WideScreen(MovieLayout):
    """ WideScreen Movie Layout

    [             FRONT_CAMERA             ]
    [LEFT_CAMERA][REAR_CAMERA][RIGHT_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.rear = True
        self.scale = 1 / 2
        self.font_scale = 4
        self._front_width = 1280
        self._front_height = 960
        self._left_width = 1280
        self._left_height = 960
        self._right_width = 1280
        self._right_height = 960
        self._rear_width = 1280
        self._rear_height = 960

        self.left_options = ""
        self.front_options = ""
        self.right_options = ""
        self.rear_options = ""

        self.swap_left_right = False

    @property
    def front_width(self):
        return (
            (self.left_width + self.right_width + self.rear_width) * self.front
            if self.rear
            else super().front_width
        )

    @property
    def front_height(self):
        return (
            (self.left_height + self.right_height + self.rear_height) * self.front
            if self.rear
            else super().front_height
        )

    @property
    def get_front_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (
            (self.offset, self.offset)
            if self.rear
            else (x_pos + width + self.offset, self.offset)
        )

    @property
    def get_left_xy(self):
        return (
            (self.offset, self.front_height + self.offset)
            if self.rear
            else (self.offset, self.offset)
        )

    @property
    def get_right_xy(self):
        return (
            (
                self.rear_x + self.rear_width + self.offset,
                self.front_height + self.offset,
            )
            if self.rear
            else (self.front_x + self.front_width + self.offset, self.offset)
        )

    @property
    def get_rear_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (x_pos + width + self.offset, self.front_height + self.offset)


class FullScreen(MovieLayout):
    """ FullScreen Movie Layout

                     [FRONT_CAMERA]
        [LEFT_CAMERA][REAR_CAMERA][RIGHT_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.rear = True
        self.scale = 1 / 2
        self.font_scale = 4
        self.front_width = 1280
        self.front_height = 960
        self.left_width = 1280
        self.left_height = 960
        self.right_width = 1280
        self.right_height = 960
        self.rear_width = 1280
        self.rear_height = 960

        self.left_options = ""
        self.front_options = ""
        self.right_options = ""
        self.rear_options = ""

        self.swap_left_right = False

    @property
    def video_height(self):
        if self.perspective:
            height = int(max(3 / 2 * self.left_height, 3 / 2 * self.right_height))
            height = (
                max(height, self.rear_height) + self.front_height
                if self.rear
                else height + self.front_height
            )
            height = height + 5 if height > 0 else 0
            return height
        else:
            return max(
                self.left_y + self.left_height,
                self.front_y + self.front_height,
                self.right_y + self.right_height,
                self.rear_y + self.rear_height,
            )

    @property
    def get_front_xy(self):
        if self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (
            max(0, int((x_pos + width) / 2 - (self.front_width / 2))) + self.offset,
            self.offset,
        )

    @property
    def get_left_xy(self):
        return (self.offset, self.front_height + self.offset)

    @property
    def get_right_xy(self):
        return (
            self.rear_x + self.rear_width + self.offset,
            self.front_height + self.offset,
        )

    @property
    def get_rear_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (x_pos + width + self.offset, self.front_height + self.offset)


class Cross(MovieLayout):
    """ Cross Movie Layout

             [FRONT_CAMERA]
        [LEFT_CAMERA][RIGHT_CAMERA]
             [REAR_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.rear = True
        self.scale = 1 / 2
        self.font_scale = 4
        self.front_width = 1280
        self.front_height = 960
        self.left_width = 1280
        self.left_height = 960
        self.right_width = 1280
        self.right_height = 960
        self.rear_width = 1280
        self.rear_height = 960

        self.left_options = ""
        self.front_options = ""
        self.right_options = ""
        self.rear_options = ""

        self.swap_left_right = False

    @property
    def video_height(self):
        if self.perspective:
            height = int(max(3 / 2 * self.left_height, 3 / 2 * self.right_height))
            # If output from both left and rear cameras is shown then we're going to make it so that
            # the rear camera is moved up to fit more between both.
            if self.left and self.rear:
                height = int(height / 3 * 2)

            return height + self.rear_height + self.front_height + self.offset
        else:
            return max(
                self.left_y + self.left_height,
                self.front_y + self.front_height,
                self.right_y + self.right_height,
                self.rear_y + self.rear_height,
            )

    @property
    def get_front_xy(self):
        if self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (
            max(0, int((x_pos + width) / 2 - (self.front_width / 2))) + self.offset,
            self.offset,
        )

    @property
    def get_left_xy(self):
        return (self.offset, self.front_height + self.offset)

    @property
    def get_right_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (x_pos + width + self.offset, self.front_height + self.offset)

    @property
    def get_rear_xy(self):
        if self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        if self.perspective:
            height = int(max(3 / 2 * self.left_height, 3 / 2 * self.right_height))
            # If output from both left and rear cameras is shown then we're going to make it so that
            # the rear camera is moved up to fit more between both.
            if self.left and self.right:
                height = int(height / 3 * 2)
        else:
            height = max(self.left_height, self.right_height)

        return (
            max(0, int((x_pos + width) / 2 - (self.rear_width / 2))) + self.offset,
            height + self.front_height + self.offset,
        )


class Diamond(MovieLayout):
    """ Diamond Movie Layout

                    [FRONT_CAMERA]
        [LEFT_CAMERA]            [RIGHT_CAMERA]
                    [REAR_CAMERA]
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.rear = True
        self.scale = 1 / 2
        self.font_scale = 2
        self.front_width = 1280
        self.front_height = 960
        self.left_width = 1280
        self.left_height = 960
        self.right_width = 1280
        self.right_height = 960
        self.rear_width = 1280
        self.rear_height = 960

        self.left_options = ""
        self.front_options = ""
        self.right_options = ""
        self.rear_options = ""

        self.swap_left_right = False

        self._font_valign = VALIGN["MIDDLE"]

    @property
    def font_halign(self):
        if self._font_halign == HALIGN["CENTER"]:
            # Change alignment to left or right if one of the left/right cameras is excluded.
            if (self.left and not self.right) or (self.right and not self.left):
                x_pos = int(
                    max(
                        self.front_x + self.front_width / 2,
                        self.rear_x + self.rear_width / 2,
                    )
                )
                return f"({x_pos} - text_w / 2)"

        return self._font_halign

    @font_halign.setter
    def font_halign(self, alignment):
        super(Diamond, self.__class__).font_halign.fset(self, alignment)

    @property
    def font_valign(self):
        if self._font_valign == VALIGN["MIDDLE"]:
            if self.front and not self.rear:
                return f"({self.front_y + self.front_height} + 5)"
            elif self.rear and not self.front:
                return f"({self.rear_y} - 5 - text_h)"

        return self._font_valign

    @font_valign.setter
    def font_valign(self, alignment):
        super(Diamond, self.__class__).font_valign.fset(self, alignment)

    @property
    def video_height(self):
        if self.perspective:
            return (
                int(
                    max(
                        3 / 2 * self.left_height + self.left_y,
                        3 / 2 * self.right_height + self.right_y,
                        self.front_height + self.front_y,
                        self.rear_height + self.rear_y,
                    )
                )
                + self.offset
            )
        else:
            return max(
                self.left_y + self.left_height,
                self.front_y + self.front_height,
                self.right_y + self.right_height,
                self.rear_y + self.rear_height,
            )

    @property
    def get_front_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (x_pos + width + self.offset, self.offset)

    @property
    def get_left_xy(self):
        return (self.offset, int(self.front_height / 2) + self.offset)

    @property
    def get_right_xy(self):
        return (
            max(self.front_x + self.front_width, self.rear_x + self.rear_width)
            + self.offset,
            int(self.front_height / 2) + self.offset,
        )

    @property
    def get_rear_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (
            x_pos + width + self.offset,
            max(
                int(self.front_height / 2 + (self.left_height / 2)),
                int(self.front_height / 2 + (self.right_height / 2)),
                self.front_height,
            )
            + self.offset
            + int((16 * self.font_scale * self.scale)),
        )


class Perspective(MovieLayout):
    """ Perspective Movie Layout

                       [FRONT_CAMERA]
        \[LEFT_CAMERA]\[REAR_CAMERA]/[RIGHT_CAMERA]/
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.rear = True
        self.scale = 1 / 4
        self.font_scale = 4
        self.front_width = 1280
        self.front_height = 960
        self.left_width = 1280
        self.left_height = 960
        self.right_width = 1280
        self.right_height = 960
        self.rear_width = 1280
        self.rear_height = 960

        self._left_options = (
            ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000, "
            "perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:"
            "x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination"
        )
        self.front_options = ""
        self._right_options = (
            ", pad=iw+4:3/2*ih:-1:ih/8:0x00000000,"
            "perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:"
            "x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination"
        )
        self.rear_options = ""

        self.swap_left_right = False

    @property
    def video_width(self):
        width = self.left_width + 5 * self.left + self.right_width + 5 * self.right
        width += (
            (self.rear_width + 5 * self.rear)
            if self.rear
            else (self.front_width + 5 * self.front)
        )
        return width + 5 if width > 0 else 0

    @property
    def video_height(self):
        height = int(max(3 / 2 * self.left_height, 3 / 2 * self.right_height))
        height = (
            max(height, self.rear_height) + self.front_height
            if self.rear
            else max(height, self.front_height)
        )
        height = height + 5 if height > 0 else 0
        return height

    @property
    def get_front_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (x_pos + width + 5, 5)

    @property
    def get_left_xy(self):
        return (5, self.front_height + 5)

    @property
    def get_right_xy(self):
        return (
            (self.rear_x + self.rear_width * self.rear + 5, self.front_height + 5)
            if self.rear
            else (
                self.front_x + self.front_width * self.front + 5,
                self.front_height + 5,
            )
        )

    @property
    def get_rear_xy(self):
        if not self.swap_left_right:
            x_pos = self.left_x
            width = self.left_width
        else:
            x_pos = self.right_x
            width = self.right_width

        return (x_pos + width + 5, self.front_height + 5)


class Diagonal(MovieLayout):
    """ Perspective Movie Layout
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.scale = 1 / 4
        self.font_scale = 4
        self.front_width = 1280
        self.front_height = 960
        self.left_width = 1280
        self.left_height = 960
        self.right_width = 1280
        self.right_height = 960

        self.left_options = (
            ", pad=iw+4:11/6*ih:-1:30:0x00000000,"
            "perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:"
            "x2=0:y2=6*H/5:x3=W:y3=410:sense=destination"
        )
        self.front_options = ""
        self.right_options = (
            ", pad=iw+4:11/6*ih:-1:30:0x00000000,"
            "perspective=x0=0:y0=-3/44*H:x1=W:y1=1*H/5:"
            "x2=0:y2=410:x3=W:y3=6*H/5:sense=destination"
        )

        self.swap_left_right = False

    @property
    def front_width(self):
        return super() + 5 if self.front else 0

    @property
    def left_width(self):
        return super() + 5 if self.left else 0

    @property
    def right_width(self):
        return super() + 5 if self.right else 0

    @property
    def video_width(self):
        width = self.front_width + self.left_width + self.right_width
        return width + 5 if width > 0 else 0

    @property
    def video_height(self):
        height = int(
            max(
                (6 * self.left_height / 5 + 1 * self.left_height / 5),
                self.front_height,
                (self.right_height / 5 + 6 * self.right_height / 5),
            )
        )
        height = height + 5 if height > 0 else 0
        return height

    @property
    def front_x(self):
        return self.left_width + 5

    @property
    def front_y(self):
        return 5

    @property
    def left_x(self):
        return 5

    @property
    def left_y(self):
        return 5

    @property
    def right_x(self):
        return self.front_x + self.front_width

    @property
    def right_y(self):
        return 5


class MyArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, arg_line):
        return arg_line.split()


# noinspection PyCallByClass,PyProtectedMember,PyProtectedMember
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


def check_latest_release(include_beta):
    """ Checks GitHub for latest release """

    url = "{url}/repos/{owner}/{repo}/releases".format(
        url=GITHUB["URL"], owner=GITHUB["owner"], repo=GITHUB["repo"]
    )

    if not include_beta:
        url = url + "/latest"
    try:
        releases = requests.get(url)
    except requests.exceptions.RequestException as exc:
        print("Unable to check for latest release: {exc}".format(exc=exc))
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
            return teslacamfolder, partition.mountpoint

    return None, None


def get_movie_files(source_folder, exclude_subdirs, video_settings):
    """ Find all the clip files within folder (and subfolder if requested) """

    folder_list = {}
    total_folders = 0

    for pathname in source_folder:
        if os.path.isdir(pathname):
            isfile = False
            if exclude_subdirs:
                # Retrieve all the video files in current path:
                search_path = os.path.join(pathname, "*.mp4")
                files = [
                    filename
                    for filename in glob(search_path)
                    if not os.path.basename(filename).startswith(".")
                ]
                print("Discovered {} files, retrieving clip data.".format(len(files)))
            else:
                # Search all sub folder.
                files = []
                for folder, _, filenames in os.walk(pathname, followlinks=True):
                    total_folders = total_folders + 1
                    for filename in (
                        filename
                        for filename in filenames
                        if not os.path.basename(filename).startswith(".")
                        and fnmatch(filename, "*.mp4")
                    ):
                        files.append(os.path.join(folder, filename))

                print(
                    "Discovered {} folders containing total of {} files, retrieving clip data.".format(
                        total_folders, len(files)
                    )
                )
        else:
            files = [pathname]
            isfile = True

        # Now go through and get timestamps etc..
        for file in sorted(files):
            # Strip path so that we just have the filename.
            movie_folder, movie_filename = os.path.split(file)

            # And now get the timestamp of the filename.
            filename_timestamp = movie_filename.rsplit("-", 1)[0]

            movie_file_list = folder_list.get(movie_folder, {})

            # Check if we already processed this timestamp.
            if movie_file_list.get(filename_timestamp) is not None:
                # Already processed this timestamp, moving on.
                continue

            video_info = {
                "front_camera": {
                    "filename": None,
                    "duration": None,
                    "timestamp": None,
                    "include": False,
                },
                "left_camera": {
                    "filename": None,
                    "duration": None,
                    "timestamp": None,
                    "include": False,
                },
                "right_camera": {
                    "filename": None,
                    "duration": None,
                    "timestamp": None,
                    "include": False,
                },
                "rear_camera": {
                    "filename": None,
                    "duration": None,
                    "timestamp": None,
                    "include": False,
                },
            }

            front_filename = str(filename_timestamp) + "-front.mp4"
            front_path = os.path.join(movie_folder, front_filename)

            left_filename = str(filename_timestamp) + "-left_repeater.mp4"
            left_path = os.path.join(movie_folder, left_filename)

            right_filename = str(filename_timestamp) + "-right_repeater.mp4"
            right_path = os.path.join(movie_folder, right_filename)

            rear_filename = str(filename_timestamp) + "-rear_view.mp4"
            rear_path = os.path.join(movie_folder, rear_filename)

            # Get meta data for each video to determine creation time and duration.
            metadata = get_metadata(
                video_settings["ffmpeg_exec"],
                [front_path, left_path, right_path, rear_path],
            )

            # Move on to next one if nothing received.
            if not metadata:
                continue

            # Get the longest duration:
            duration = 0
            video_timestamp = None
            for item in metadata:
                _, filename = os.path.split(item["filename"])
                if filename == front_filename:
                    camera = "front_camera"
                    video_filename = front_filename
                    include_clip = (
                        item["include"]
                        if video_settings["video_layout"].front
                        else False
                    )
                elif filename == left_filename:
                    camera = "left_camera"
                    video_filename = left_filename
                    include_clip = (
                        item["include"]
                        if video_settings["video_layout"].left
                        else False
                    )
                elif filename == right_filename:
                    camera = "right_camera"
                    video_filename = right_filename
                    include_clip = (
                        item["include"]
                        if video_settings["video_layout"].right
                        else False
                    )
                elif filename == rear_filename:
                    camera = "rear_camera"
                    video_filename = rear_filename
                    include_clip = (
                        item["include"]
                        if video_settings["video_layout"].rear
                        else False
                    )
                else:
                    continue

                # Store duration and timestamp
                video_info[camera].update(
                    filename=video_filename,
                    duration=item["duration"],
                    timestamp=item["timestamp"],
                    include=include_clip,
                )

                # Only check duration and timestamp if this file is not corrupt and if we include this camera
                # in our output.
                if include_clip:
                    # Figure out which one has the longest duration
                    duration = (
                        item["duration"] if item["duration"] > duration else duration
                    )

                    # Figure out starting timestamp
                    if video_timestamp is None:
                        video_timestamp = item["timestamp"]
                    else:
                        video_timestamp = (
                            item["timestamp"]
                            if item["timestamp"] < video_timestamp
                            else video_timestamp
                        )

            if video_timestamp is None:
                # Firmware version 2019.16 changed filename timestamp format.
                if len(filename_timestamp) == 16:
                    # This is for before version 2019.16
                    video_timestamp = datetime.strptime(
                        filename_timestamp, "%Y-%m-%d_%H-%M"
                    )
                    video_timestamp = video_timestamp.astimezone(get_localzone())
                else:
                    # This is for version 2019.16 and later
                    video_timestamp = datetime.strptime(
                        filename_timestamp, "%Y-%m-%d_%H-%M-%S"
                    )
                    video_timestamp = video_timestamp.astimezone(timezone.utc)

            movie_info = {
                "movie_folder": movie_folder,
                "timestamp": video_timestamp,
                "duration": duration,
                "video_info": video_info,
                "file_only": isfile,
            }

            movie_file_list.update({filename_timestamp: movie_info})
            folder_list.update({movie_folder: movie_file_list})

    return folder_list


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

    # Don't run ffmpeg if nothing to check for.
    if not metadata:
        return metadata

    ffmpeg_command.append("-hide_banner")

    command_result = run(ffmpeg_command, capture_output=True, text=True)
    metadata_iterator = iter(metadata)
    input_counter = 0

    video_timestamp = None
    wait_for_input_line = True
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

            metadata_item.update(
                {"timestamp": video_timestamp, "duration": duration, "include": include}
            )

            wait_for_input_line = True

    return metadata


def create_intermediate_movie(
    filename_timestamp,
    video,
    folder_timestamps,
    video_settings,
    clip_number,
    total_clips,
):
    """ Create intermediate movie files. This is the merging of the 3 camera

    video files into 1 video file. """
    # We first stack (combine the 3 different camera video files into 1
    # and then we concatenate.
    front_camera = (
        os.path.join(
            video["movie_folder"], video["video_info"]["front_camera"]["filename"]
        )
        if (
            video["video_info"]["front_camera"]["filename"] is not None
            and video["video_info"]["front_camera"]["include"]
        )
        else None
    )

    left_camera = (
        os.path.join(
            video["movie_folder"], video["video_info"]["left_camera"]["filename"]
        )
        if (
            video["video_info"]["left_camera"]["filename"] is not None
            and video["video_info"]["left_camera"]["include"]
        )
        else None
    )

    right_camera = (
        os.path.join(
            video["movie_folder"], video["video_info"]["right_camera"]["filename"]
        )
        if (
            video["video_info"]["right_camera"]["filename"] is not None
            and video["video_info"]["right_camera"]["include"]
        )
        else None
    )

    rear_camera = (
        os.path.join(
            video["movie_folder"], video["video_info"]["rear_camera"]["filename"]
        )
        if (
            video["video_info"]["rear_camera"]["filename"] is not None
            and video["video_info"]["rear_camera"]["include"]
        )
        else None
    )

    if (
        front_camera is None
        and left_camera is None
        and right_camera is None
        and rear_camera is None
    ):
        return None, 0, True

    # Determine if this clip is to be included based on potential start and end timestamp/offsets that were provided.
    # Clip starting time is between the start&end times we're looking for
    # or Clip end time is between the start&end time we're looking for.
    # or Starting time is between start&end clip time
    # or End time is between start&end clip time
    starting_timestmp = video["timestamp"]
    ending_timestmp = starting_timestmp + timedelta(seconds=video["duration"])
    if not (
        folder_timestamps[0] <= starting_timestmp <= folder_timestamps[1]
        or folder_timestamps[0] <= ending_timestmp <= folder_timestamps[1]
        or starting_timestmp <= folder_timestamps[0] <= ending_timestmp
        or starting_timestmp <= folder_timestamps[1] <= ending_timestmp
    ):
        # This clip is not in-between the timestamps we want, skip it.
        return None, 0, True

    # Determine if we need to do an offset of the starting timestamp
    starting_offset = 0
    ffmpeg_offset_command = []
    clip_duration = video["duration"]

    # This clip falls in between the start and end timestamps to include.
    # Set offsets if required
    if video["timestamp"] < folder_timestamps[0]:
        # Starting timestamp is withing this clip.
        starting_offset = (folder_timestamps[0] - video["timestamp"]).total_seconds()
        starting_timestmp = folder_timestamps[0]
        ffmpeg_offset_command = ["-ss", str(starting_offset)]
        clip_duration = video["duration"] - starting_offset

    # Adjust duration if end of clip's timestamp is after ending timestamp we need.
    if video["timestamp"] + timedelta(seconds=video["duration"]) > folder_timestamps[1]:
        # Duration has to be cut.
        clip_duration = (
            folder_timestamps[1]
            - (video["timestamp"] + timedelta(seconds=starting_offset))
        ).total_seconds()
        ffmpeg_offset_command += ["-t", str(clip_duration)]

    # Confirm if files exist, if not replace with nullsrc
    input_count = 0
    if left_camera is not None and os.path.isfile(left_camera):
        ffmpeg_left_command = ffmpeg_offset_command + ["-i", left_camera]
        ffmpeg_left_camera = ";[0:v] " + video_settings["left_camera"]
        input_count += 1
    else:
        ffmpeg_left_command = []
        ffmpeg_left_camera = (
            video_settings["background"].format(
                duration=clip_duration,
                speed=video_settings["movie_speed"],
                width=video_settings["video_layout"].left_width,
                height=video_settings["video_layout"].left_height,
            )
            + "[left]"
            if video_settings["video_layout"].left
            else ""
        )

    if front_camera is not None and os.path.isfile(front_camera):
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
                width=video_settings["video_layout"].front_width,
                height=video_settings["video_layout"].front_height,
            )
            + "[front]"
            if video_settings["video_layout"].front
            else ""
        )

    if right_camera is not None and os.path.isfile(right_camera):
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
                width=video_settings["video_layout"].right_width,
                height=video_settings["video_layout"].right_height,
            )
            + "[right]"
            if video_settings["video_layout"].right
            else ""
        )

    if rear_camera is not None and os.path.isfile(rear_camera):
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
                width=video_settings["video_layout"].rear_width,
                height=video_settings["video_layout"].rear_height,
            )
            + "[rear]"
            if video_settings["video_layout"].rear
            else ""
        )

    local_timestamp = video["timestamp"].astimezone(get_localzone())

    # Check if target video file exist if skip existing.
    file_already_exist = False
    if video_settings["skip_existing"]:
        temp_movie_name = (
            os.path.join(video_settings["target_folder"], filename_timestamp) + ".mp4"
        )
        if os.path.isfile(temp_movie_name):
            file_already_exist = True
        elif (
            not video_settings["keep_intermediate"]
            and video_settings["temp_dir"] is not None
        ):
            temp_movie_name = (
                os.path.join(video_settings["temp_dir"], filename_timestamp) + ".mp4"
            )
            if os.path.isfile(temp_movie_name):
                file_already_exist = True

        if file_already_exist:
            print(
                "\t\tSkipping clip {clip_number}/{total_clips} from {timestamp} "
                "and {duration} seconds as it already exist.".format(
                    clip_number=clip_number + 1,
                    total_clips=total_clips,
                    timestamp=local_timestamp.strftime("%x %X"),
                    duration=int(clip_duration),
                )
            )
            # Get actual duration of our new video, required for chapters when concatenating.
            metadata = get_metadata(video_settings["ffmpeg_exec"], [temp_movie_name])
            duration = metadata[0]["duration"] if metadata else video["duration"]

            return temp_movie_name, duration, True
    else:
        target_folder = (
            video_settings["temp_dir"]
            if not video_settings["keep_intermediate"]
            and video_settings["temp_dir"] is not None
            else video_settings["target_folder"]
        )
        temp_movie_name = os.path.join(target_folder, filename_timestamp) + ".mp4"

    print(
        "\t\tProcessing clip {clip_number}/{total_clips} from {timestamp} "
        "and {duration} seconds long.".format(
            clip_number=clip_number + 1,
            total_clips=total_clips,
            timestamp=local_timestamp.strftime("%x %X"),
            duration=int(clip_duration),
        )
    )

    epoch_timestamp = int(starting_timestmp.timestamp())

    ffmpeg_filter = (
        video_settings["base"].format(
            duration=clip_duration, speed=video_settings["movie_speed"]
        )
        + ffmpeg_left_camera
        + ffmpeg_front_camera
        + ffmpeg_right_camera
        + ffmpeg_rear_camera
        + video_settings["clip_positions"]
        + video_settings["timestamp_text"].format(epoch_time=epoch_timestamp)
        + video_settings["ffmpeg_speed"]
        + video_settings["ffmpeg_motiononly"]
    )

    ffmpeg_command = (
        [video_settings["ffmpeg_exec"]]
        + ffmpeg_left_command
        + ffmpeg_front_command
        + ffmpeg_right_command
        + ffmpeg_rear_command
        + ["-filter_complex", ffmpeg_filter]
        + ["-map", f"[{video_settings['input_clip']}]"]
        + video_settings["other_params"]
    )

    ffmpeg_command = ffmpeg_command + ["-y", temp_movie_name]
    # print(ffmpeg_command)
    # Run the command.
    try:
        run(ffmpeg_command, capture_output=True, check=True)
    except CalledProcessError as exc:
        print(
            "\t\t\tError trying to create clip for {base_name}. RC: {rc}\n"
            "\t\t\tCommand: {command}\n"
            "\t\t\tError: {stderr}\n\n".format(
                base_name=os.path.join(video["movie_folder"], filename_timestamp),
                rc=exc.returncode,
                command=exc.cmd,
                stderr=exc.stderr,
            )
        )
        return None, 0, False

    # Get actual duration of our new video, required for chapters when concatenating.
    metadata = get_metadata(video_settings["ffmpeg_exec"], [temp_movie_name])
    duration = metadata[0]["duration"] if metadata else video["duration"]

    return temp_movie_name, duration, True


def create_movie(clips_list, movie_filename, video_settings, chapter_offset):
    """ Concatenate provided movie files into 1."""
    # Just return if there are no clips.
    if not clips_list:
        return None, None

    # Go through the list of clips to create the command and content for chapter meta file.
    ffmpeg_join_filehandle, ffmpeg_join_filename = mkstemp(suffix=".txt", text=True)
    total_clips = 0
    meta_content = ""
    meta_start = 0
    total_videoduration = 0
    chapter_offset = chapter_offset * 1000000000
    with os.fdopen(ffmpeg_join_filehandle, "w") as fp:
        # Loop through the list sorted by video timestamp.
        for video_clip in sorted(
            clips_list, key=lambda video: video["video_timestamp"]
        ):
            if not os.path.isfile(video_clip["video_filename"]):
                print(
                    "\t\tFile {} does not exist anymore, skipping.".format(
                        video_clip["video_filename"]
                    )
                )
                continue

            # Add this file in our join list.
            fp.write(
                "file '"
                + video_clip["video_filename"]
                + "'{linesep}".format(linesep=os.linesep)
            )
            total_clips = total_clips + 1
            title = video_clip["video_timestamp"].astimezone(get_localzone())
            # For duration need to also calculate if video was sped-up or slowed down.
            video_duration = int(video_clip["video_duration"] * 1000000000)
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
                        linesep=os.linesep,
                        start=0,
                        end=chapter_start - 1,
                        title="Start",
                    )
                )

            meta_content = (
                meta_content + "[CHAPTER]{linesep}"
                "TIMEBASE=1/1000000000{linesep}"
                "START={start}{linesep}"
                "END={end}{linesep}"
                "title={title}{linesep}".format(
                    linesep=os.linesep,
                    start=chapter_start,
                    end=meta_start + video_duration,
                    title=title.strftime("%x %X"),
                )
            )
            meta_start = meta_start + 1 + video_duration

    if total_clips == 0:
        print("\t\tError: No valid clips to merge found.")
        return None, None

    # Write out the meta data file.
    meta_content = ";FFMETADATA1" + os.linesep + meta_content

    ffmpeg_meta_filehandle, ffmpeg_meta_filename = mkstemp(suffix=".txt", text=True)
    with os.fdopen(ffmpeg_meta_filehandle, "w") as fp:
        fp.write(meta_content)

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

    ffmpeg_params = ffmpeg_params + [
        "-metadata",
        f"description=Created by tesla_dashcam {VERSION_STR}",
    ]

    ffmpeg_command = (
        [video_settings["ffmpeg_exec"]] + ffmpeg_params + ["-y", movie_filename]
    )

    # print(ffmpeg_command)
    try:
        run(ffmpeg_command, capture_output=True, check=True)
    except CalledProcessError as exc:
        print(
            "\t\tError trying to create movie {base_name}. RC: {rc}\n"
            "\t\tCommand: {command}\n"
            "\t\tError: {stderr}\n\n".format(
                base_name=movie_filename,
                rc=exc.returncode,
                command=exc.cmd,
                stderr=exc.stderr,
            )
        )
        movie_filename = None
        duration = 0
    else:
        # Get actual duration of our new video, required for chapters when concatenating.
        metadata = get_metadata(video_settings["ffmpeg_exec"], [movie_filename])
        duration = metadata[0]["duration"] if metadata else total_videoduration

    # Remove temp join file.
    try:
        os.remove(ffmpeg_join_filename)
    except:
        pass

    # Remove temp join file.
    try:
        os.remove(ffmpeg_meta_filename)
    except:
        pass

    return movie_filename, duration


def make_folder(parameter, folder):
    # Create folder if not already existing.
    if not os.path.isdir(folder):
        current_path, add_folder = os.path.split(folder)
        if add_folder == "":
            current_path, add_folder = os.path.split(current_path)

        # If path does not exist in which to create folder then exit.
        if not os.path.isdir(current_path):
            print(
                f"Path {current_path} for parameter {parameter} does not exist, please provide a valid path."
            )
            return False

        try:
            os.mkdir(folder)
        except OSError as exc:
            print(
                f"Error creating folder {add_folder} at location {current_path} for parameter {parameter}"
            )
            return False

    return True


def delete_intermediate(movie_files):
    """ Delete the files provided in list """
    for file in movie_files:
        if file is not None:
            if os.path.isfile(file):
                try:
                    os.remove(file)
                except OSError as exc:
                    print("\t\tError trying to remove file {}: {}".format(file, exc))
            elif os.path.isdir(file):
                # This is more specific for Mac but won't hurt on other platforms.
                if os.path.exists(os.path.join(file, ".DS_Store")):
                    try:
                        os.remove(os.path.join(file, ".DS_Store"))
                    except:
                        pass

                try:

                    os.rmdir(file)
                except OSError as exc:
                    print("\t\tError trying to remove folder {}: {}".format(file, exc))


def process_folders(folders, video_settings, delete_source):
    """ Process all clips found within folders. """
    start_time = timestamp()

    total_clips = 0
    for folder_number, folder_name in enumerate(sorted(folders)):
        total_clips = total_clips + len(folders[folder_name])
    print(
        "There are {total_folders} folders with {total_clips} clips to "
        "process.".format(total_folders=len(folders), total_clips=total_clips)
    )

    # Loop through all the folders.
    dashcam_clips = []
    for folder_number, folder_name in enumerate(sorted(folders)):
        files = folders[folder_name]

        # Ensure the clips are sorted based on video timestamp.
        sorted_video_clips = sorted(files, key=lambda video: files[video]["timestamp"])

        # Get the start and ending timestamps, we add duration to
        # last timestamp to get true ending.
        first_clip_tmstp = files[sorted_video_clips[0]]["timestamp"]
        last_clip_tmstp = files[sorted_video_clips[-1]]["timestamp"] + timedelta(
            seconds=files[sorted_video_clips[-1]]["duration"]
        )

        # Skip this folder if we it does not fall within provided timestamps.
        if (
            video_settings["start_timestamp"] is not None
            and last_clip_tmstp < video_settings["start_timestamp"]
        ):
            # Clips from this folder are from before start timestamp requested.
            continue

        if (
            video_settings["end_timestamp"] is not None
            and first_clip_tmstp > video_settings["end_timestamp"]
        ):
            # Clips from this folder are from after end timestamp requested.
            continue

        # Determine the starting and ending timestamps for the clips in this folder based on start/end timestamps
        # provided and offsets.
        folder_start_timestmp = (
            timedelta(seconds=video_settings["start_offset"]) + first_clip_tmstp
        )
        # Use provided start timestamp if it is after folder timestamp + offset
        folder_start_timestmp = (
            video_settings["start_timestamp"]
            if video_settings["start_timestamp"] is not None
            and video_settings["start_timestamp"] > folder_start_timestmp
            else folder_start_timestmp
        )

        # Figure out potential end timestamp for clip based on offset and end timestamp.
        folder_end_timestmp = last_clip_tmstp - timedelta(
            seconds=video_settings["end_offset"]
        )
        # Use provided end timestamp if it is before folder timestamp - offset
        folder_end_timestmp = (
            video_settings["end_timestamp"]
            if video_settings["end_timestamp"] is not None
            and video_settings["end_timestamp"] < folder_end_timestmp
            else folder_end_timestmp
        )

        # Put them together to create the filename for the folder.
        movie_filename = (
            folder_start_timestmp.astimezone(get_localzone()).strftime(
                "%Y-%m-%dT%H-%M-%S"
            )
            + "_"
            + folder_end_timestmp.astimezone(get_localzone()).strftime(
                "%Y-%m-%dT%H-%M-%S"
            )
        )

        # Now add full path to it.
        movie_filename = (
            os.path.join(video_settings["target_folder"], movie_filename) + ".mp4"
        )

        # Do not process the files from this folder if we're to skip it if
        # the target movie file already exist.
        if video_settings["skip_existing"] and os.path.isfile(movie_filename):
            print(
                "\tSkipping folder {folder} as {filename} is already "
                "created ({folder_number}/{total_folders})".format(
                    folder=folder_name,
                    filename=movie_filename,
                    folder_number=folder_number + 1,
                    total_folders=len(folders),
                )
            )

            # Get actual duration of our new video, required for chapters when concatenating.
            metadata = get_metadata(video_settings["ffmpeg_exec"], [movie_filename])
            movie_duration = metadata[0]["duration"] if metadata else 0
            dashcam_clips.append(
                {
                    "video_timestamp": first_clip_tmstp,
                    "video_filename": movie_filename,
                    "video_duration": movie_duration,
                }
            )
            continue

        print(
            "\tProcessing {total_clips} clips in folder {folder} "
            "({folder_number}/{total_folders})".format(
                total_clips=len(files),
                folder=folder_name,
                folder_number=folder_number + 1,
                total_folders=len(folders),
            )
        )

        # Loop through all the files within the folder.
        folder_clips = []
        delete_folder_clips = []
        delete_folder_files = delete_source
        delete_file_list = []
        folder_timestamp = None

        for clip_number, filename_timestamp in enumerate(sorted_video_clips):
            video_timestamp_info = files[filename_timestamp]
            folder_timestamp = (
                video_timestamp_info["timestamp"]
                if folder_timestamp is None
                else folder_timestamp
            )

            clip_name, clip_duration, files_processed = create_intermediate_movie(
                filename_timestamp,
                video_timestamp_info,
                (folder_start_timestmp, folder_end_timestmp),
                video_settings,
                clip_number,
                len(files),
            )
            if clip_name is not None:
                if video_timestamp_info["file_only"]:
                    # When file only there is no concatenation at the folder
                    # level, will only happen at the higher level if requested.
                    dashcam_clips.append(
                        {
                            "video_timestamp": video_timestamp_info["timestamp"],
                            "video_filename": clip_name,
                            "video_duration": clip_duration,
                        }
                    )
                else:
                    # Movie was created, store name for concatenation.
                    folder_clips.append(
                        {
                            "video_timestamp": video_timestamp_info["timestamp"],
                            "video_filename": clip_name,
                            "video_duration": clip_duration,
                        }
                    )

                    # Add clip for deletion only if it's name is not the
                    # same as the resulting movie filename
                    if clip_name != movie_filename:
                        delete_folder_clips.append(clip_name)
            elif not files_processed:
                delete_folder_files = False

            if files_processed:
                # Add the files to our list for removal.
                video_info = video_timestamp_info["video_info"]
                if video_info["front_camera"]["filename"] is not None:
                    delete_file_list.append(
                        os.path.join(
                            video_timestamp_info["movie_folder"],
                            video_info["front_camera"]["filename"],
                        )
                    )

                if video_info["left_camera"]["filename"] is not None:
                    delete_file_list.append(
                        os.path.join(
                            video_timestamp_info["movie_folder"],
                            video_info["left_camera"]["filename"],
                        )
                    )

                if video_info["right_camera"]["filename"] is not None:
                    delete_file_list.append(
                        os.path.join(
                            video_timestamp_info["movie_folder"],
                            video_info["right_camera"]["filename"],
                        )
                    )

                if video_info["rear_camera"]["filename"] is not None:
                    delete_file_list.append(
                        os.path.join(
                            video_timestamp_info["movie_folder"],
                            video_info["rear_camera"]["filename"],
                        )
                    )

        # All clips in folder have been processed, merge those clips
        # together now.
        movie_name = None
        if folder_clips:
            print("\t\tCreating movie {}, please be patient.".format(movie_filename))

            movie_name, movie_duration = create_movie(
                folder_clips, movie_filename, video_settings, 0
            )

        # Delete the source files if stated to delete.
        # We only do so if there were no issues in processing the clips
        if delete_folder_files and (
            (folder_clips and movie_name is not None) or not folder_clips
        ):
            print(
                "\t\tDeleting files and folder {folder_name}".format(
                    folder_name=folder_name
                )
            )
            delete_intermediate(delete_file_list)
            # And delete the folder
            delete_intermediate([folder_name])

        # Add this one to our list for final concatenation
        if movie_name is not None:
            dashcam_clips.append(
                {
                    "video_timestamp": folder_timestamp,
                    "video_filename": movie_name,
                    "video_duration": movie_duration,
                }
            )
            # Delete the intermediate files we created.
            if not video_settings["keep_intermediate"]:
                delete_intermediate(delete_folder_clips)

            print(
                "\tMovie {base_name} for folder {folder_name} with duration {duration} is "
                "ready.".format(
                    base_name=movie_name,
                    folder_name=folder_name,
                    duration=str(timedelta(seconds=int(movie_duration))),
                )
            )

    # Now that we have gone through all the folders merge.
    # We only do this if merge is enabled OR if we only have 1 clip and for
    # output a specific filename was provided.
    movie_name = None
    if dashcam_clips:
        if video_settings["merge_subdirs"] or (
            len(folders) == 1 and video_settings["target_filename"] is not None
        ):

            if video_settings["movie_filename"] is not None:
                movie_filename = video_settings["movie_filename"]
            elif video_settings["target_filename"] is not None:
                movie_filename = video_settings["target_filename"]
            else:
                folder, movie_filename = os.path.split(video_settings["target_folder"])
                # If there was a trailing separator provided then it will be
                # empty, redo split then.
                if movie_filename == "":
                    movie_filename = os.path.split(folder)[1]

            movie_filename = os.path.join(
                video_settings["target_folder"], movie_filename
            )

            # Make sure it ends in .mp4
            if os.path.splitext(movie_filename)[1] != ".mp4":
                movie_filename = movie_filename + ".mp4"

            print("\tCreating movie {}, please be patient.".format(movie_filename))

            movie_name, movie_duration = create_movie(
                dashcam_clips,
                movie_filename,
                video_settings,
                video_settings["chapter_offset"],
            )

        if movie_name is not None:
            print(
                "Movie {base_name} with duration {duration} has been created, enjoy.".format(
                    base_name=movie_name,
                    duration=str(timedelta(seconds=int(movie_duration))),
                )
            )
        else:
            print(
                "All folders have been processed, resulting movie files are "
                "located in {target_folder}".format(
                    target_folder=video_settings["target_folder"]
                )
            )
    else:
        print("No clips found.")

    end_time = timestamp()
    real = int((end_time - start_time))

    print("Total processing time: {real}".format(real=str(timedelta(seconds=real))))
    if video_settings["notification"]:
        if movie_name is not None:
            notify(
                "TeslaCam",
                "Completed",
                "{total_folders} folder{folders} with {total_clips} "
                "clip{clips} have been processed, movie {movie_name} has "
                "been created.".format(
                    folders="" if len(folders) < 2 else "s",
                    total_folders=len(folders),
                    clips="" if total_clips < 2 else "s",
                    total_clips=total_clips,
                    movie_name=video_settings["target_folder"],
                ),
            )
        else:
            notify(
                "TeslaCam",
                "Completed",
                "{total_folders} folder{folders} with {total_clips} "
                "clip{clips} have been processed, {target_folder} contains "
                "resulting files.".format(
                    folders="" if len(folders) < 2 else "s",
                    total_folders=len(folders),
                    clips="" if total_clips < 2 else "s",
                    total_clips=total_clips,
                    target_folder=video_settings["target_folder"],
                ),
            )
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
        print("Failed in notifification: ", exc)


def notify_windows(title, subtitle, message):
    """ Notification on Windows """

    # Section commented out, waiting to see if it really does not work on Windows 7
    # This works only on Windows 10 9r Windows Server 2016/2019. Skipping for everything else
    #    from platform import win32_ver
    #    if win32_ver()[0] != 10:
    #        return

    try:
        from win10toast import ToastNotifier

        if TOASTER_INSTANCE is None:
            TOASTER_INSTANCE = ToastNotifier()

        TOASTER_INSTANCE.show_toast(
            threaded=True,
            title="{} {}".format(title, subtitle),
            msg=message,
            duration=5,
            icon_path=resource_path("tesla_dashcam.ico"),
        )

        run(
            [
                "notify-send",
                '"{title} {subtitle}"'.format(title=title, subtitle=subtitle),
                '"{}"'.format(message),
            ]
        )
    except Exception:
        pass


def notify_linux(title, subtitle, message):
    """ Notification on Linux """
    try:
        run(
            [
                "notify-send",
                '"{title} {subtitle}"'.format(title=title, subtitle=subtitle),
                '"{}"'.format(message),
            ]
        )
    except Exception as exc:
        print("Failed in notifification: ", exc)


def notify(title, subtitle, message):
    """ Call function to send notification based on OS """
    if sys.platform == "darwin":
        notify_macos(title, subtitle, message)
    elif sys.platform == "win32":
        notify_windows(title, subtitle, message)
    elif sys.platform == "linux":
        notify_linux(title, subtitle, message)


def main() -> None:
    """ Main function """

    internal_ffmpeg = getattr(sys, "frozen", None) is not None
    ffmpeg_default = resource_path(FFMPEG.get(sys.platform, "ffmpeg"))

    movie_folder = os.path.join(str(Path.home()), MOVIE_HOMEDIR.get(sys.platform), "")

    # Check if ffmpeg exist, if not then hope it is in default path or
    # provided.
    if not os.path.isfile(ffmpeg_default):
        internal_ffmpeg = False
        ffmpeg_default = FFMPEG.get(sys.platform, "ffmpeg")

    epilog = (
        "This program leverages ffmpeg which is included. See "
        "https://ffmpeg.org/ for more information on ffmpeg"
        if internal_ffmpeg
        else "This program requires ffmpeg which can be "
        "downloaded from: "
        "https://ffmpeg.org/download.html"
    )

    parser = MyArgumentParser(
        description="tesla_dashcam - Tesla DashCam & Sentry Video Creator",
        epilog=epilog,
        formatter_class=SmartFormatter,
        fromfile_prefix_chars="@",
    )

    parser.add_argument(
        "--version", action="version", version=" %(prog)s " + VERSION_STR
    )

    parser.add_argument(
        "source",
        type=str,
        nargs="*",
        help="Folder(s) containing the saved camera "
        "files. Filenames can be provided as well to "
        "manage individual clips.",
    )

    sub_dirs = parser.add_mutually_exclusive_group()
    sub_dirs.add_argument(
        "--exclude_subdirs",
        dest="exclude_subdirs",
        action="store_true",
        help="Do not search sub folders for video files to process.",
    )

    sub_dirs.add_argument(
        "--merge",
        dest="merge_subdirs",
        action="store_true",
        help="Merge the video files from different " "folders into 1 big video file.",
    )

    filter_group = parser.add_argument_group(
        title="Timestamp Restriction",
        description="Restrict video to be between start and/or end timestamps. Timestamp to be provided in a ISO-8601"
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
        title="Clip offsets", description="Start and/or end offsets"
    )

    offset_group.add_argument(
        "--start_offset",
        dest="start_offset",
        type=int,
        help="Starting offset in seconds. ",
    )

    offset_group.add_argument(
        "--end_offset", dest="end_offset", type=int, help="Ending offset in seconds."
    )

    parser.add_argument(
        "--chapter_offset",
        dest="chapter_offset",
        type=int,
        default=0,
        help="Offset in seconds for chapters in merged video. Negative offset is # of seconds before the end of the "
        "subdir video, positive offset if # of seconds after the start of the subdir video.",
    )

    parser.add_argument(
        "--output",
        required=False,
        default=movie_folder,
        type=str,
        help="R|Path/Filename for the new movie file. "
        "Intermediate files will be stored in same "
        "folder." + os.linesep,
    )

    parser.add_argument(
        "--keep-intermediate",
        dest="keep_intermediate",
        action="store_true",
        help="Do not remove the intermediate video files that are created",
    )

    parser.add_argument(
        "--skip_existing",
        dest="skip_existing",
        action="store_true",
        help="Skip creating encoded video file if it already exist. Note that only existence is checked, not if "
        "layout etc. are the same.",
    )

    parser.add_argument(
        "--delete_source",
        dest="delete_source",
        action="store_true",
        help="Delete the processed files on the " "TeslaCam drive.",
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
        "--layout",
        required=False,
        choices=["WIDESCREEN", "FULLSCREEN", "PERSPECTIVE", "CROSS", "DIAMOND"],
        default="FULLSCREEN",
        help="R|Layout of the created video.\n"
        "    FULLSCREEN: Front camera center top, "
        "side cameras underneath it with rear camera between side camera.\n"
        "    WIDESCREEN: Front camera on top with side and rear cameras smaller underneath it.\n"
        "    PERSPECTIVE: Similar to FULLSCREEN but then with side cameras in perspective.\n"
        "    CROSS: Front camera center top, side cameras underneath, and rear camera center bottom.\n"
        "    DIAMOND: Front camera center top, side cameras below front camera left and right of front, and rear camera center bottom.\n",
    )
    parser.add_argument(
        "--perspective",
        dest="perspective",
        action="store_true",
        help="Show side cameras in perspective.",
    )
    parser.set_defaults(perspective=False)

    parser.add_argument(
        "--scale",
        dest="clip_scale",
        type=float,
        help="R|Set camera clip scale, scale of 1 "
        "is 1280x960 camera clip. "
        "Defaults:\n"
        "    WIDESCREEN: 1/3 (front 1280x960, others 426x320, video is "
        "1280x960)\n"
        "    FULLSCREEN: 1/2 (640x480, video is "
        "1280x960)\n"
        "    PERSPECTIVE: 1/4 (320x240, video is "
        "980x380)\n"
        "    CROSS: 1/2 (640x480, video is "
        "1280x1440)\n"
        "    DIAMOND: 1/2 (640x480, video is "
        "1280x1440)\n",
    )

    parser.add_argument(
        "--motion_only",
        dest="motion_only",
        action="store_true",
        help="Fast-forward through video when there is no motion.",
    )

    mirror_or_rear = parser.add_mutually_exclusive_group()

    mirror_or_rear.add_argument(
        "--mirror",
        dest="mirror",
        action="store_true",
        help="Video from side cameras as if being "
        "viewed through the sidemirrors. Cannot "
        "be used in combination with --rear.",
    )
    mirror_or_rear.add_argument(
        "--rear",
        dest="rear",
        action="store_true",
        help="Video from side cameras as if looking "
        "backwards. Cannot be used in "
        "combination with --mirror.",
    )
    parser.set_defaults(mirror=True)
    parser.set_defaults(rear=False)

    swap_cameras = parser.add_mutually_exclusive_group()
    swap_cameras.add_argument(
        "--swap",
        dest="swap",
        action="store_const",
        const=1,
        help="Swap left and right cameras, default when "
        "layout FULLSCREEN with --rear option is "
        "chosen.",
    )
    swap_cameras.add_argument(
        "--no-swap",
        dest="swap",
        action="store_const",
        const=0,
        help="Do not swap left and right cameras, " "default with all other options.",
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

    speed_group = parser.add_mutually_exclusive_group()
    speed_group.add_argument(
        "--slowdown",
        dest="slow_down",
        type=int,
        help="Slow down video output. Accepts a number "
        "that is then used as multiplier, "
        "providing 2 means half the speed.",
    )
    speed_group.add_argument(
        "--speedup",
        dest="speed_up",
        type=int,
        help="Speed up the video. Accepts a number "
        "that is then used as a multiplier, "
        "providing 2 means twice the speed.",
    )

    encoding_group = parser.add_mutually_exclusive_group()
    encoding_group.add_argument(
        "--encoding",
        required=False,
        choices=["x264", "x265"],
        default="x264",
        help="R|Encoding to use for video creation.\n"
        "    x264: standard encoding, can be "
        "viewed on most devices but results in "
        "bigger file.\n"
        "    x265: newer encoding standard but "
        "not all devices support this yet.\n",
    )
    encoding_group.add_argument(
        "--enc",
        required=False,
        type=str,
        help="R|Provide a custom encoding for video "
        "creation.\n"
        "Note: when using this option the --gpu "
        "option is ignored. To use GPU hardware "
        "acceleration specify a encoding that "
        "provides this.",
    )

    gpu_help = (
        "R|Use GPU acceleration, only enable if "
        "supported by hardware.\n"
        " MAC: All MACs with Haswell CPU or later  "
        "support this (Macs after 2013).\n"
        "      See following link as well: \n"
        "         https://en.wikipedia.org/wiki/List_of_"
        "Macintosh_models_grouped_by_CPU_type#Haswell\n"
    )

    if sys.platform == "darwin":
        parser.add_argument("--no-gpu", dest="gpu", action="store_true", help=gpu_help)
    else:
        parser.add_argument("--gpu", dest="gpu", action="store_true", help=gpu_help)

        parser.add_argument(
            "--gpu_type",
            choices=["nvidia", "intel", "RPi"],
            help="Type of graphics card (GPU) in the system. This determines the encoder that will be used."
            "This parameter is mandatory if --gpu is provided.",
        )

    parser.add_argument(
        "--no-faststart",
        dest="faststart",
        action="store_true",
        help="Do not enable flag faststart on the resulting video files. Use this when using a network share and errors occur during encoding.",
    )

    timestamp_group = parser.add_argument_group(
        title="Timestamp", description="Options for " "timestamp:"
    )
    timestamp_group.add_argument(
        "--no-timestamp",
        dest="no_timestamp",
        action="store_true",
        help="Include timestamp in video",
    )

    timestamp_group.add_argument(
        "--halign",
        required=False,
        choices=["LEFT", "CENTER", "RIGHT"],
        help="Horizontal alignment for timestamp",
    )

    timestamp_group.add_argument(
        "--valign",
        required=False,
        choices=["TOP", "MIDDLE", "BOTTOM"],
        help="Vertical Alignment for timestamp",
    )

    timestamp_group.add_argument(
        "--font",
        required=False,
        type=str,
        default=DEFAULT_FONT.get(sys.platform, None),
        help="Fully qualified filename (.ttf) to the "
        "font to be chosen for timestamp.",
    )

    timestamp_group.add_argument(
        "--fontsize",
        required=False,
        type=int,
        help="Font size for timestamp. Default is " "scaled based on video scaling.",
    )

    timestamp_group.add_argument(
        "--fontcolor",
        required=False,
        type=str,
        default="white",
        help="R|Font color for timestamp. Any color "
        "is "
        "accepted as a color string or RGB "
        "value.\n"
        "Some potential values are:\n"
        "    white\n"
        "    yellowgreen\n"
        "    yellowgreen@0.9\n"
        "    Red\n:"
        "    0x2E8B57\n"
        "For more information on this see "
        "ffmpeg "
        "documentation for color: "
        "https://ffmpeg.org/ffmpeg-utils.html#"
        "Color",
    )

    quality_group = parser.add_argument_group(
        title="Video Quality",
        description="Options for " "resulting video " "quality and size:",
    )

    quality_group.add_argument(
        "--quality",
        required=False,
        choices=["LOWEST", "LOWER", "LOW", "MEDIUM", "HIGH"],
        default="LOWER",
        help="Define the quality setting for the "
        "video, higher quality means bigger file "
        "size but might not be noticeable.",
    )

    quality_group.add_argument(
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
        help="Speed to optimize video. Faster speed "
        "results in a bigger file. This does not "
        "impact the quality of the video, "
        "just how "
        "much time is used to compress it.",
    )

    if internal_ffmpeg:
        parser.add_argument(
            "--ffmpeg",
            required=False,
            type=str,
            help="Full path and filename for alternative " "ffmpeg.",
        )
    else:
        parser.add_argument(
            "--ffmpeg",
            required=False,
            type=str,
            default=ffmpeg_default,
            help="Path and filename for ffmpeg. Specify if "
            "ffmpeg is not within path.",
        )

    monitor_group = parser.add_argument_group(
        title="Monitor for TeslaDash Cam drive",
        description="Parameters to monitor for a drive to be attached with "
        "folder TeslaCam in the root.",
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
        help="Enable monitoring and exit once drive "
        "with TeslaCam folder has been attached "
        "and files processed.",
    )

    monitor_group.add_argument(
        "--monitor_trigger",
        required=False,
        type=str,
        help="Trigger file to look for instead of waiting for drive to be attached. Once file is discovered then "
        "processing will start, file will be deleted when processing has been completed. If source is not "
        "provided then folder where file is located will be used as source.",
    )

    update_check_group = parser.add_argument_group(
        title="Update Check", description="Check for updates"
    )

    update_check_group.add_argument(
        "--check_for_update",
        dest="check_for_updates",
        action="store_true",
        help="Check for updates, do not do " "anything else.",
    )

    update_check_group.add_argument(
        "--no-check_for_update",
        dest="no_check_for_updates",
        action="store_true",
        help="A check for new updates is "
        "performed every time. With this "
        "parameter that can be disabled",
    )

    update_check_group.add_argument(
        "--include_test",
        dest="include_beta",
        action="store_true",
        help="Include test (beta) releases " "when checking for updates.",
    )

    args = parser.parse_args()

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
                            "New {beta}release {release} is available. You are "
                            "on version {version}".format(
                                beta=beta,
                                release=release_info.get("tag_name"),
                                version=VERSION_STR,
                            ),
                        )
                    release_notes = (
                        "Use --check_for_update to get latest " "release notes."
                    )

                print(
                    "New {beta}release {release} is available for download "
                    "({url}). You are currently on {version}. {rel_note}".format(
                        beta=beta,
                        release=release_info.get("tag_name"),
                        url=release_info.get("html_url"),
                        version=VERSION_STR,
                        rel_note=release_notes,
                    )
                )

                if args.check_for_updates:
                    print(
                        "You can download the new release from: {url}".format(
                            url=release_info.get("html_url")
                        )
                    )
                    print(
                        "Release Notes:\n {release_notes}".format(
                            release_notes=release_info.get("body")
                        )
                    )
                    return
            else:
                if args.check_for_updates:
                    print(
                        "{version} is the latest release available.".format(
                            version=VERSION_STR
                        )
                    )
                    return
        else:
            print("Did not retrieve latest version info.")

    ffmpeg = ffmpeg_default if getattr(args, "ffmpeg", None) is None else args.ffmpeg
    if which(ffmpeg) is None:
        print(
            f"ffmpeg is a requirement, unable to find {ffmpeg} executable. Please ensure it exist and is located"
            f"within PATH environment."
        )

    mirror_sides = ""
    if args.rear:
        side_camera_as_mirror = False
    else:
        side_camera_as_mirror = True

    if side_camera_as_mirror:
        mirror_sides = ", hflip"

    black_base = "color=duration={duration}:"
    black_size = "s={width}x{height}:c=black "

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
            layout_settings = Diagonal()

        layout_settings.perspective = args.perspective

    if args.clip_scale is not None and args.clip_scale > 0:
        layout_settings.scale = args.clip_scale

    # Determine if left and right cameras should be swapped or not.
    if args.swap is None:
        # Default is set based on layout chosen.
        if args.layout == "FULLSCREEN":
            # FULLSCREEN is different, if doing mirror then default should
            # not be swapping. If not doing mirror then default should be
            # to swap making it seem more like a "rear" camera.
            layout_settings.swap_left_right = not side_camera_as_mirror
    else:
        layout_settings.swap_left_right = args.swap

    layout_settings.front = not args.no_front
    layout_settings.left = not args.no_left
    layout_settings.right = not args.no_right
    layout_settings.rear = not args.no_rear

    if args.halign is not None:
        layout_settings.font_halign = args.halign

    if args.valign is not None:
        layout_settings.font_valign = args.valign

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
    if layout_settings.left:
        ffmpeg_left_camera = (
            "setpts=PTS-STARTPTS, "
            "scale={clip_width}x{clip_height} {mirror}{options}"
            " [left]".format(
                clip_width=layout_settings.left_width,
                clip_height=layout_settings.left_height,
                mirror=mirror_sides,
                options=layout_settings.left_options,
            )
        )

        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][left] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [left1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.left_x,
                y_pos=layout_settings.left_y,
            )
        )
        input_clip = "left1"

    ffmpeg_front_camera = ""
    if layout_settings.front:
        ffmpeg_front_camera = (
            "setpts=PTS-STARTPTS, "
            "scale={clip_width}x{clip_height} {options}"
            " [front]".format(
                clip_width=layout_settings.front_width,
                clip_height=layout_settings.front_height,
                options=layout_settings.front_options,
            )
        )
        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][front] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [front1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.front_x,
                y_pos=layout_settings.front_y,
            )
        )
        input_clip = "front1"

    ffmpeg_right_camera = ""
    if layout_settings.right:
        ffmpeg_right_camera = (
            "setpts=PTS-STARTPTS, "
            "scale={clip_width}x{clip_height} {mirror}{options}"
            " [right]".format(
                clip_width=layout_settings.right_width,
                clip_height=layout_settings.right_height,
                mirror=mirror_sides,
                options=layout_settings.right_options,
            )
        )
        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][right] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [right1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.right_x,
                y_pos=layout_settings.right_y,
            )
        )
        input_clip = "right1"

    ffmpeg_rear_camera = ""
    if layout_settings.rear:
        ffmpeg_rear_camera = (
            "setpts=PTS-STARTPTS, "
            "scale={clip_width}x{clip_height} {options}"
            " [rear]".format(
                clip_width=layout_settings.rear_width,
                clip_height=layout_settings.rear_height,
                options=layout_settings.rear_options,
            )
        )
        ffmpeg_video_position = (
            ffmpeg_video_position
            + ";[{input_clip}][rear] overlay=eof_action=pass:repeatlast=0:"
            "x={x_pos}:y={y_pos} [rear1]".format(
                input_clip=input_clip,
                x_pos=layout_settings.rear_x,
                y_pos=layout_settings.rear_y,
            )
        )
        input_clip = "rear1"

    filter_counter = 0
    filter_string = ";[{input_clip}] {filter} [tmp{filter_counter}]"
    ffmpeg_timestamp = ""
    if not args.no_timestamp:
        if args.font is not None and args.font != "":
            if not os.path.isfile(args.font):
                print(
                    f"Provided font file {args.font} does exist, please provide a valid font file."
                )
                return
            font_file = args.font
        else:
            font_file = DEFAULT_FONT.get(sys.platform, None)
            if font_file is None:
                print("Unable to get a font file. Please provide valid font file.")
                return

            if not os.path.isfile(font_file):
                print(
                    f"Seems default font file {font_file} does exist, please provide a font file."
                )
                return

        ffmpeg_timestamp = f"drawtext=fontfile={font_file}:"

        # If fontsize is not provided then scale font size based on scaling
        # of video clips, otherwise use fixed font size.
        if args.fontsize is None or args.fontsize == 0:
            fontsize = 16 * layout_settings.font_scale * layout_settings.scale
        else:
            fontsize = args.fontsize

        ffmpeg_timestamp = (
            ffmpeg_timestamp + "fontcolor={fontcolor}:fontsize={fontsize}:"
            "borderw=2:bordercolor=black@1.0:"
            "x={halign}:y={valign}:".format(
                fontcolor=args.fontcolor,
                fontsize=fontsize,
                valign=layout_settings.font_valign,
                halign=layout_settings.font_halign,
            )
        )

        ffmpeg_timestamp = (
            ffmpeg_timestamp + "text='%{{pts\:localtime\:{epoch_time}\:%x %X}}'"
        )

        ffmpeg_timestamp = filter_string.format(
            input_clip=input_clip,
            filter=ffmpeg_timestamp,
            filter_counter=filter_counter,
        )
        input_clip = f"tmp{filter_counter}"
        filter_counter += 1

    speed = args.slow_down if args.slow_down is not None else ""
    speed = 1 / args.speed_up if args.speed_up is not None else speed
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
            filter=f"mpdecimate, setpts=N/FRAME_RATE/TB",
            filter_counter=filter_counter,
        )
        input_clip = f"tmp{filter_counter}"
        filter_counter += 1

    ffmpeg_params = ["-preset", args.compression, "-crf", MOVIE_QUALITY[args.quality]]

    use_gpu = args.gpu
    if sys.platform == "darwin":
        use_gpu = not args.gpu

    video_encoding = []
    if args.enc is None:
        encoding = args.encoding
        # GPU acceleration enabled
        if use_gpu:
            print("GPU acceleration is enabled")
            if sys.platform == "darwin":
                video_encoding = video_encoding + ["-allow_sw", "1"]
                encoding = encoding + "_mac"
            else:
                if args.gpu_type is None:
                    print(
                        "Parameter --gpu_type is mandatory when parameter --use_gpu is used."
                    )
                    return

                encoding = encoding + "_" + args.gpu_type

            bit_rate = str(int(10000 * layout_settings.scale)) + "K"
            video_encoding = video_encoding + ["-b:v", bit_rate]

        video_encoding = video_encoding + ["-c:v", MOVIE_ENCODING[encoding]]
    else:
        video_encoding = video_encoding + ["-c:v", args.enc]

    ffmpeg_params = ffmpeg_params + video_encoding

    # Set metadata
    ffmpeg_params = ffmpeg_params + [
        "-metadata",
        f"description=Created by tesla_dashcam {VERSION_STR}",
    ]

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
    target_folder = os.path.abspath(target_folder)

    # Ensure folder if not already exist and if not can be created
    if not make_folder("--output", target_folder):
        return

    temp_folder = args.temp_dir
    if temp_folder is not None:
        # Convert temp folder to absolute path if relative path has been provided
        temp_folder = os.path.abspath(args.temp_dir)

        if not make_folder("--temp_dir", temp_folder):
            return

    # Set the run type based on arguments.
    runtype = "RUN"
    if args.monitor:
        runtype = "MONITOR"
    elif args.monitor_once:
        runtype = "MONITOR_ONCE"
    monitor_file = args.monitor_trigger

    # If no source provided then set to MONITOR_ONCE and we're only going to
    # take SavedClips and SentryClips
    source_list = args.source
    if not source_list:
        source_list = ["SavedClips", "SentryClips"]
        if runtype == "RUN":
            runtype = "MONITOR_ONCE"

    start_timestamp = None
    if args.start_timestamp is not None:
        start_timestamp = isoparse(args.start_timestamp)
        if start_timestamp.tzinfo is None:
            start_timestamp = start_timestamp.astimezone(get_localzone())

    end_timestamp = None
    if args.end_timestamp is not None:
        end_timestamp = isoparse(args.end_timestamp)
        if end_timestamp.tzinfo is None:
            end_timestamp = end_timestamp.astimezone(get_localzone())

    start_offset = abs(args.start_offset) if args.start_offset is not None else 0
    end_offset = abs(args.end_offset) if args.end_offset is not None else 0

    video_settings = {
        "source_folder": source_list,
        "output": args.output,
        "target_folder": target_folder,
        "target_filename": target_filename,
        "temp_dir": temp_folder,
        "run_type": runtype,
        "merge_subdirs": args.merge_subdirs,
        "chapter_offset": args.chapter_offset,
        "movie_filename": None,
        "keep_intermediate": args.keep_intermediate,
        "notification": args.system_notification,
        "movie_layout": args.layout,
        "movie_speed": speed,
        "video_encoding": video_encoding,
        "movie_encoding": args.encoding,
        "movie_compression": args.compression,
        "movie_quality": args.quality,
        "background": ffmpeg_black_video,
        "ffmpeg_exec": ffmpeg,
        "base": ffmpeg_base,
        "video_layout": layout_settings,
        "clip_positions": ffmpeg_video_position,
        "timestamp_text": ffmpeg_timestamp,
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
        "start_offset": start_offset,
        "end_timestamp": end_timestamp,
        "end_offset": end_offset,
        "skip_existing": args.skip_existing,
    }

    # If we constantly run and monitor for drive added or not.
    if video_settings["run_type"] in ["MONITOR", "MONITOR_ONCE"]:

        video_settings.update({"skip_existing": True})

        trigger_exist = False
        if monitor_file is None:
            print("Monitoring for TeslaCam Drive to be inserted. Press CTRL-C to stop")
        else:
            print(
                "Monitoring for trigger {} to exist. Press CTRL-C to stop".format(
                    monitor_file
                )
            )
        while True:
            try:
                # Monitoring for disk to be inserted and not for a file.
                if monitor_file is None:
                    source_folder, source_partition = get_tesladashcam_folder()
                    if source_folder is None:
                        # Nothing found, sleep for 1 minute and check again.
                        if trigger_exist:
                            print("TeslaCam drive has been ejected.")
                            print(
                                "Monitoring for TeslaCam Drive to be inserted. "
                                "Press CTRL-C to stop"
                            )

                        sleep(MONITOR_SLEEP_TIME)
                        trigger_exist = False
                        continue

                    # As long as TeslaCam drive is still attached we're going to
                    # keep on waiting.
                    if trigger_exist:
                        sleep(MONITOR_SLEEP_TIME)
                        continue

                    # Got a folder, append what was provided as source unless
                    # . was provided in which case everything is done.
                    if video_settings["source_folder"][0] != ".":
                        source_folder = os.path.join(
                            source_folder, video_settings["source_folder"][0]
                        )

                    message = "TeslaCam folder found on {partition}.".format(
                        partition=source_partition
                    )
                else:
                    # Wait till trigger file exist (can also be folder).
                    if not os.path.exists(monitor_file):
                        sleep(MONITOR_SLEEP_TIME)
                        trigger_exist = False
                        continue

                    if trigger_exist:
                        sleep(MONITOR_SLEEP_TIME)
                        continue

                    message = "Trigger {} exist.".format(monitor_file)
                    trigger_exist = True

                    # Set monitor path, make sure what was provided is a file first otherwise get path.
                    monitor_path = monitor_file
                    if os.path.isfile(monitor_file):
                        monitor_path, _ = os.path.split(monitor_file)

                    # If . is provided then source folder is path where monitor file exist.
                    if video_settings["source_folder"][0] == ".":
                        source_folder = monitor_path
                    else:
                        # If source path provided is absolute then use that for source path
                        if os.path.isabs(video_settings["source_folder"][0]):
                            source_folder = video_settings["source_folder"][0]
                        else:
                            # Path provided is relative, hence based on path of trigger file.
                            source_folder = os.path.join(
                                monitor_path, video_settings["source_folder"][0]
                            )

                print(message)
                if args.system_notification:
                    notify("TeslaCam", "Started", message)

                print("Retrieving all files from {}".format(source_folder))
                folders = get_movie_files(
                    [source_folder], args.exclude_subdirs, video_settings
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

                    video_settings.update({"movie_filename": movie_filename})
                else:
                    # Set filename to right now if no filename provided.
                    movie_filename = (
                        datetime.today().strftime("%Y-%m-%d_%H_%M")
                        if video_settings["target_filename"] is None
                        else video_settings["target_filename"]
                    )
                    video_settings.update({"movie_filename": movie_filename})

                process_folders(folders, video_settings, args.delete_source)

                print("Processing of movies has completed.")
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
                                    "Error trying to remove trigger file {}: {}".format(
                                        monitor_file, exc
                                    )
                                )
                            trigger_exist = False

                    print("Exiting monitoring as asked process once.")
                    break

                if monitor_file is None:
                    trigger_exist = True
                    print(
                        "Waiting for TeslaCam Drive to be ejected. Press "
                        "CTRL-C to stop"
                    )
                else:
                    if os.path.isfile(monitor_file):
                        try:
                            os.remove(monitor_file)
                        except OSError as exc:
                            print(
                                "Error trying to remove trigger file {}: {}".format(
                                    monitor_file, exc
                                )
                            )
                            break
                        trigger_exist = False

                        print(
                            "Monitoring for trigger {}. Press CTRL-C to stop".format(
                                monitor_file
                            )
                        )
                    else:
                        print(
                            "Waiting for trigger {} to be removed. Press CTRL-C to stop".format(
                                monitor_file
                            )
                        )

            except KeyboardInterrupt:
                print("Monitoring stopped due to CTRL-C.")
                break
    else:
        folders = get_movie_files(
            video_settings["source_folder"], args.exclude_subdirs, video_settings
        )

        # Set filename to right now if no filename provided.
        movie_filename = (
            datetime.today().strftime("%Y-%m-%d_%H_%M")
            if video_settings["target_filename"] is None
            else video_settings["target_filename"]
        )
        video_settings.update({"movie_filename": movie_filename})

        process_folders(folders, video_settings, args.delete_source)


if sys.version_info < (3, 7):
    print(
        f"Python version 3.7 or higher is required, you have: {sys.version}. Please update your Python version."
    )
    sys.exit(1)

sys.exit(main())
