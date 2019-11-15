"""
Merges the 3 Tesla Dashcam and Sentry camera video files into 1 video. If
then further concatenates the files together to make 1 movie.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from glob import glob
from pathlib import Path
from re import search
from shlex import split as shlex_split
from shutil import which
from subprocess import CalledProcessError, run
from tempfile import mkstemp
from time import sleep, time as timestamp
from typing import List, Optional

import requests
from dateutil.parser import isoparse
from psutil import disk_partitions
from tzlocal import get_localzone

_LOGGER = logging.getLogger(__name__)

# TODO: Move everything into classes and separate files. For example,
#  update class, font class (for timestamp), folder class, clip class (
#  combining front, left, and right info), file class (for individual file).
#  Clip class would then have to merge the camera clips, folder class would
#  have to concatenate the merged clips. Settings class to take in all settings
# TODO: Create kind of logger or output classes for output. That then allows
#  different ones to be created based on where it should go to (stdout,
#  log file, ...).

VERSION = {"major": 0, "minor": 1, "patch": 16, "beta": -1}
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

# noinspection PyPep8
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
    "x265_intel": "hevc_qsv",
    "x265_RPi": "h265",
}

DEFAULT_FONT = {
    "darwin": "/Library/Fonts/Arial Unicode.ttf",
    "win32": "/Windows/Fonts/arial.ttf",
    "cygwin": "/cygdrive/c/Windows/Fonts/arial.ttf",
    "linux": "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
}

HALIGN = {"LEFT": "10", "CENTER": "(w/2-text_w/2)", "RIGHT": "(w-text_w)"}

VALIGN = {"TOP": "10", "MIDDLE": "(h/2-(text_h/2))", "BOTTOM": "(h-(text_h*2))"}

TOASTER_INSTANCE = None


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
            _LOGGER.debug(f"Folder TeslaCam found on partition {partition.mountpoint}.")
            return teslacamfolder, partition.mountpoint
        _LOGGER.debug(f"No TeslaCam folder on partition {partition.mountpoint}.")
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
                print(f"Discovered {len(files)} files in {pathname}")
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
                    f"Discovered {total_folders} folders containing total of {len(files)} files in {pathname}"
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

            _LOGGER.debug(
                f"Checking camera files in folder {movie_folder} with timestamp {filename_timestamp}"
            )
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

            rear_filename = str(filename_timestamp) + "-back.mp4"
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
                        if video_settings["video_layout"].cameras("Front").include
                        else False
                    )
                elif filename == left_filename:
                    camera = "left_camera"
                    video_filename = left_filename
                    include_clip = (
                        item["include"]
                        if video_settings["video_layout"].cameras("Left").include
                        else False
                    )
                elif filename == right_filename:
                    camera = "right_camera"
                    video_filename = right_filename
                    include_clip = (
                        item["include"]
                        if video_settings["video_layout"].cameras("Right").include
                        else False
                    )
                elif filename == rear_filename:
                    camera = "rear_camera"
                    video_filename = rear_filename
                    include_clip = (
                        item["include"]
                        if video_settings["video_layout"].cameras("Rear").include
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
        _LOGGER.debug(
            f'No front, left, right, and rear camera clip exist for {video["timestamp"]}'
        )
        return None, 0, True

    if video_settings["video_layout"].swap_left_right:
        left_camera, right_camera = right_camera, left_camera

    if video_settings["video_layout"].swap_front_rear:
        front_camera, rear_camera = rear_camera, front_camera

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
        _LOGGER.debug(
            f"Clip timestamp from {starting_timestmp} to {ending_timestmp} not "
            f"between {folder_timestamps[0]} and {folder_timestamps[1]}"
        )
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
                width=video_settings["video_layout"].cameras("Left").width,
                height=video_settings["video_layout"].cameras("Left").height,
            )
            + "[left]"
            if video_settings["video_layout"].cameras("Left").include
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
                width=video_settings["video_layout"].cameras("Front").width,
                height=video_settings["video_layout"].cameras("Front").height,
            )
            + "[front]"
            if video_settings["video_layout"].cameras("Front").include
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
                width=video_settings["video_layout"].cameras("Right").width,
                height=video_settings["video_layout"].cameras("Right").height,
            )
            + "[right]"
            if video_settings["video_layout"].cameras("Right").include
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
                width=video_settings["video_layout"].cameras("Rear").width,
                height=video_settings["video_layout"].cameras("Rear").height,
            )
            + "[rear]"
            if video_settings["video_layout"].cameras("Rear").include
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
        + ["-loglevel", "error"]
        + ffmpeg_left_command
        + ffmpeg_front_command
        + ffmpeg_right_command
        + ffmpeg_rear_command
        + ["-filter_complex", ffmpeg_filter]
        + ["-map", f"[{video_settings['input_clip']}]"]
        + video_settings["other_params"]
    )

    ffmpeg_command = ffmpeg_command + ["-y", temp_movie_name]
    _LOGGER.debug(f"FFMPEG Command: {ffmpeg_command}")
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
        _LOGGER.debug("Clip list is empty")
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
        [video_settings["ffmpeg_exec"]]
        + ["-loglevel", "error"]
        + ffmpeg_params
        + ["-y", movie_filename]
    )

    _LOGGER.debug(f"FFMPEG Command: {ffmpeg_command}")
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
        except OSError:
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
                    # noinspection PyBroadException,PyPep8
                    try:
                        os.remove(os.path.join(file, ".DS_Store"))
                    except:
                        _LOGGER.debug(f"Failed to remove .DS_Store from {file}")
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
            _LOGGER.debug(
                f"Clips in folder end at {last_clip_tmstp} which is still before "
                f'start timestamp {video_settings["start_timestamp"]}'
            )
            continue

        if (
            video_settings["end_timestamp"] is not None
            and first_clip_tmstp > video_settings["end_timestamp"]
        ):
            # Clips from this folder are from after end timestamp requested.
            _LOGGER.debug(
                f"Clips in folder start at {first_clip_tmstp} which is after "
                f'end timestamp {video_settings["end_timestamp"]}'
            )
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
        movie_duration = 0
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
    movie_duration = 0
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
    global TOASTER_INSTANCE

    # noinspection PyBroadException
    try:
        # noinspection PyUnresolvedReferences,PyPackageRequirements
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

    loglevels = dict(
        (logging.getLevelName(level), level) for level in [10, 20, 30, 40, 50]
    )

    internal_ffmpeg = getattr(sys, "frozen", None) is not None
    ffmpeg_default = resource_path(FFMPEG.get(sys.platform, "ffmpeg"))

    movie_folder = os.path.join(str(Path.home()), MOVIE_HOMEDIR.get(sys.platform), "")

    # Check if ffmpeg exist, if not then hope it is in default path or
    # provided.
    if not os.path.isfile(ffmpeg_default):
        internal_ffmpeg = False
        ffmpeg_default = FFMPEG.get(sys.platform, "ffmpeg")

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
        type=str,
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
        help="Background color for video. Can be a color string or RGB value. Also see --fontcolor.",
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

    timestamp_group = parser.add_argument_group(
        title="Timestamp",
        description="Options on how to show date/time in resulting video:",
    )
    timestamp_group.add_argument(
        "--no-timestamp",
        dest="no_timestamp",
        action="store_true",
        help="Do not show timestamp in video",
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
        help="Fully qualified filename (.ttf) to the font to be chosen for timestamp.",
    )
    timestamp_group.add_argument(
        "--fontsize",
        required=False,
        type=int,
        help="Font size for timestamp. Default is scaled based on resulting video size.",
    )
    timestamp_group.add_argument(
        "--fontcolor",
        required=False,
        type=str,
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
        help="Skip x number of seconds from start of event for resulting video.",
    )
    offset_group.add_argument(
        "--end_offset",
        dest="end_offset",
        type=int,
        help="Ignore the last x seconds of the event for resulting video",
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
        dest="merge_subdirs",
        action="store_true",
        help="Merge the video files from different folders (events) into 1 big video file.",
    )
    output_group.add_argument(
        "--keep-intermediate",
        dest="keep_intermediate",
        action="store_true",
        help="Do not remove the clip video files that are created",
    )

    advancedencoding_group = parser.add_argument_group(
        title="Advanced encoding settings", description="Advanced options for encoding"
    )

    gpu_help = (
        "R|Use GPU acceleration, only enable if supported by hardware.\n"
        " MAC: All MACs with Haswell CPU or later support this (Macs after 2013).\n"
        "      See following link as well: \n"
        "         https://en.wikipedia.org/wiki/List_of_Macintosh_models_grouped_by_CPU_type#Haswell\n"
    )

    if sys.platform == "darwin":
        advancedencoding_group.add_argument(
            "--no-gpu", dest="gpu", action="store_true", help=gpu_help
        )
    else:
        advancedencoding_group.add_argument(
            "--gpu", dest="gpu", action="store_true", help=gpu_help
        )

        advancedencoding_group.add_argument(
            "--gpu_type",
            choices=["nvidia", "intel", "RPi"],
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

    # Check that any mutual exclusive items are not both provided.
    if "speed_up" in args and "slow_down" in args:
        print(
            "Option --speed_up and option --slow_down cannot be used together, only use one of them."
        )
        return 1

    if "enc" in args and "encoding" in args:
        print(
            "Option --enc and option --encoding cannot be used together, only use one of them."
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
            f"within PATH environment or provide full path using parameter --ffmpeg."
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

    filter_counter = 0
    filter_string = ";[{input_clip}] {filter} [tmp{filter_counter}]"
    ffmpeg_timestamp = ""
    if not args.no_timestamp:
        if layout_settings.font.font is None:
            print(
                f"Unable to get a font file for platform {sys.platform}. Please provide valid font file using "
                f"--font or disable timestamp using --no-timestamp."
            )
            return

        # noinspection PyPep8
        temp_font_file = (
            f"c:\{layout_settings.font.font}"
            if sys.platform == "win32"
            else layout_settings.font.font
        )
        if not os.path.isfile(temp_font_file):
            print(
                f"Font file {temp_font_file} does not exist. Provide a valid font file using --font or"
                f" disable timestamp using --no-timestamp"
            )
            if sys.platform == "linux":
                print(
                    "You can also install the fonts using for example: apt-get install ttf-freefont"
                )
            return

        # noinspection PyPep8,PyPep8,PyPep8
        ffmpeg_timestamp = (
            ffmpeg_timestamp + f"drawtext=fontfile={layout_settings.font.font}:"
            f"fontcolor={layout_settings.font.color}:fontsize={layout_settings.font.size}:"
            "borderw=2:bordercolor=black@1.0:"
            f"x={layout_settings.font.halign}:y={layout_settings.font.valign}:"
            "text='%{{pts\:localtime\:{epoch_time}\:%x %X}}'"
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

    use_gpu = not args.gpu if sys.platform == "darwin" else args.gpu

    video_encoding = []
    if not "enc" in args:
        encoding = args.encoding if "encoding" in args else "x264"
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
        "movie_encoding": args.encoding if "encoding" in args else "x264",
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
    _LOGGER.debug(f"Video Settings {video_settings}")
    _LOGGER.debug(f"Layout Settings {layout_settings}")

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

                    message = "TeslaCam folder found on {partition}.".format(
                        partition=source_partition
                    )
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

                    message = "Trigger {} exist.".format(monitor_file)
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

                print(message)
                if args.system_notification:
                    notify("TeslaCam", "Started", message)

                if len(source_folder_list) == 1:
                    print(f"Retrieving all files from {source_folder_list[0]}")
                else:
                    print(f"Retrieving all files from: ")
                    for folder in source_folder_list:
                        print(f"                          {folder}")

                folders = get_movie_files(
                    source_folder_list, args.exclude_subdirs, video_settings
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

if __name__ == "__main__":
    sys.exit(main())
