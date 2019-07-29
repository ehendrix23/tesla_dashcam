"""
Merges the 3 Tesla Dashcam and Sentry camera video files into 1 video. If
then further concatenates the files together to make 1 movie.
"""
import argparse
import os
import shutil
import sys
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from re import search
from subprocess import CalledProcessError, run
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

VERSION = {
    'major': 0,
    'minor': 1,
    'patch': 11,
    'beta': -1,
}
VERSION_STR = 'v{major}.{minor}.{patch}'.format(
    major=VERSION['major'],
    minor=VERSION['minor'],
    patch=VERSION['patch'],
)

if VERSION['beta'] > -1:
    VERSION_STR = VERSION_STR + 'b{beta}'.format(
        beta=VERSION['beta']
    )

MONITOR_SLEEP_TIME = 5

GITHUB = {
    'URL': 'https://api.github.com',
    'owner': 'ehendrix23',
    'repo': 'tesla_dashcam',
}

FFMPEG = {
    'darwin': 'ffmpeg',
    'win32': 'ffmpeg.exe',
    'cygwin': 'ffmpeg',
    'linux': 'ffmpeg',
}

MOVIE_HOMEDIR = {
    'darwin': 'Movies/Tesla_Dashcam',
    'win32': 'Videos\Tesla_Dashcam',
    'cygwin': 'Videos/Tesla_Dashcam',
    'linux': 'Videos/Tesla_Dashcam',
}

DEFAULT_CLIP_HEIGHT = 960
DEFAULT_CLIP_WIDTH = 1280

MOVIE_QUALITY = {
    'HIGH':   '18',
    'MEDIUM': '20',
    'LOW':    '23',
    'LOWER':  '28',
    'LOWEST': '33',
}

MOVIE_ENCODING = {
    'x264': 'libx264',
    'x264_nvidia': 'h264_nvenc',
    'x264_mac': 'h264_videotoolbox',
    'x264_intel': 'h264_qsv',
    'x265': 'libx265',
    'x265_nvidia': 'hevc_nvenc',
    'x265_mac': 'hevc_videotoolbox',
    'x265_intel': 'h265_qsv',
}

DEFAULT_FONT = {
    'darwin': '/Library/Fonts/Arial.ttf',
    'win32': '/Windows/Fonts/arial.ttf',
    'cygwin': '/cygdrive/c/Windows/Fonts/arial.ttf',
    'linux': '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
}

HALIGN = {
    'LEFT':   '10',
    'CENTER': '(w/2-text_w/2)',
    'RIGHT':  '(w-text_w)',
}

VALIGN = {
    'TOP':    '10',
    'MIDDLE': '(h/2-(text_h/2))',
    'BOTTOM': '(h-(text_h*2))',
}

class MovieLayout(object):
    """ WideScreen Format
    """

    def __init__(self):
        self._include_front = False
        self._include_left = False
        self._include_right = False
        self._scale = 0
        self._font_scale = 1
        self._front_width = 0
        self._front_height = 0
        self._left_width = 0
        self._left_height = 0
        self._right_width = 0
        self._right_height = 0

        self._left_options = ''
        self._front_options = ''
        self._right_options = ''

        self._swap_left_right = False

    @property
    def front_options(self):
        return self._front_options

    @front_options.setter
    def front_options(self, options):
        self._front_options = options

    @property
    def left_options(self):
        return self._left_options

    @left_options.setter
    def left_options(self, options):
        self._left_options = options

    @property
    def right_options(self):
        return self._right_options

    @right_options.setter
    def right_options(self, options):
        self._right_options = options

    @property
    def swap_left_right(self):
        return self._swap_left_right

    @swap_left_right.setter
    def swap_left_right(self, swap):
        self._swap_left_right = swap

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
    def video_width(self):
        return max(self.left_x + self.left_width,
                   self.front_x + self.front_width,
                   self.right_x + self.right_width)

    @property
    def video_height(self):
        return max(self.left_y + self.left_height,
                   self.front_y + self.front_height,
                   self.right_y + self.right_height)

    @property
    def front_x(self):
        return 0

    @property
    def front_y(self):
        return 0

    @property
    def left_x(self):
        return 0

    @property
    def left_y(self):
        return 0

    @property
    def right_x(self):
        return 0

    @property
    def right_y(self):
        return 0

class WideScreen(MovieLayout):
    """ WideScreen Movie Layout
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.scale = 1 / 2
        self.font_scale = 2
        self.front_width = 1280
        self.front_height = 960
        self.left_width = 1280
        self.left_height = 960
        self.right_width = 1280
        self.right_height = 960

        self.left_options = ''
        self.front_options = ''
        self.right_options = ''

        self.swap_left_right = False

    @property
    def front_x(self):
        return self.left_x + self.left_width

    @property
    def front_y(self):
        return 0

    @property
    def left_x(self):
        return 0

    @property
    def left_y(self):
        return 0

    @property
    def right_x(self):
        return self.front_x + self.front_width

    @property
    def right_y(self):
        return 0


class FullScreen(MovieLayout):
    """ FullScreen Movie Layout
    """

    def __init__(self):
        super().__init__()
        self.front = True
        self.left = True
        self.right = True
        self.scale = 1 / 2
        self.font_scale = 2
        self.front_width = 1280
        self.front_height = 960
        self.left_width = 1280
        self.left_height = 960
        self.right_width = 1280
        self.right_height = 960

        self.left_options = ''
        self.front_options = ''
        self.right_options = ''

        self.swap_left_right = False

    @property
    def front_x(self):
        return max(0,
                   int((self.right_x + self.right_width) / 2 -
               self.front_width / 2))

    @property
    def front_y(self):
        return 0

    @property
    def left_x(self):
        return 0

    @property
    def left_y(self):
        return self.front_height

    @property
    def right_x(self):
        return self.left_x + self.left_width


    @property
    def right_y(self):
        return self.front_height


class Perspective(MovieLayout):
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

        self.left_options = ', pad=iw+4:3/2*ih:-1:ih/8:0x00000000, ' \
            'perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:' \
            'x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination'
        self.front_options = ''
        self.right_options = ', pad=iw+4:3/2*ih:-1:ih/8:0x00000000,' \
            'perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:' \
            'x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination'

        self.swap_left_right = False

    @property
    def video_width(self):
        width = self.front_width + 5 * self.front + \
                self.left_width + 5 * self.left + \
                self.right_width + 5 * self.right
        return width + 5 if width > 0 else 0

    @property
    def video_height(self):
        height = int(max(
            3/2*self.left_height,
            self.front_height,
            3/2*self.right_height))
        height = height + 5 if height > 0 else 0
        return height

    @property
    def front_x(self):
        return self.left_x + self.left_width + 5 * self.front

    @property
    def front_y(self):
        return 5 * self.front

    @property
    def left_x(self):
        return 5 * self.left

    @property
    def left_y(self):
        return 5 * self.left

    @property
    def right_x(self):
        return self.front_x + self.front_width * self.front + 5 * self.right

    @property
    def right_y(self):
        return 5 * self.right


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

        self.left_options = ', pad=iw+4:11/6*ih:-1:30:0x00000000,' \
            'perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:' \
            'x2=0:y2=6*H/5:x3=W:y3=410:sense=destination'
        self.front_options = ''
        self.right_options = ', pad=iw+4:11/6*ih:-1:30:0x00000000,' \
            'perspective=x0=0:y0=-3/44*H:x1=W:y1=1*H/5:' \
            'x2=0:y2=410:x3=W:y3=6*H/5:sense=destination'

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
        height = int(max(
            (6*self.left_height/5 + 1*self.left_height/5),
            self.front_height,
            (self.right_height/5+6*self.right_height/5)))
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
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)

    def _get_help_string(self, action):
        """ Call default help string """
        return argparse.ArgumentDefaultsHelpFormatter._get_help_string(self,
                                                                       action)


def check_latest_release(include_beta):
    """ Checks GitHub for latest release """

    url = '{url}/repos/{owner}/{repo}/releases'.format(
        url=GITHUB['URL'],
        owner=GITHUB['owner'],
        repo=GITHUB['repo'],
    )

    if not include_beta:
        url = url + '/latest'
    try:
        releases = requests.get(url)
    except requests.exceptions.RequestException as exc:
        print("Unable to check for latest release: {exc}".format(
            exc=exc
        ))
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
        if 'cdrom' in partition.opts or partition.fstype == '':
            continue

        teslacamfolder = os.path.join(partition.mountpoint, 'TeslaCam')
        if os.path.isdir(teslacamfolder):
            return teslacamfolder, partition.mountpoint

    return None, None


def get_movie_files(source_folder, exclude_subdirs, video_settings):
    """ Find all the clip files within folder (and subfolder if requested) """

    folder_list = {}
    for pathname in source_folder:
        if os.path.isdir(pathname):
            # Retrieve all the video files in current path:
            search_path = os.path.join(pathname, '*.mp4')
            files = (glob(search_path))

            if not exclude_subdirs:
                # Search through all sub folders as well.
                search_path = os.path.join(pathname, '*', '*.mp4')
                files = files + (glob(search_path))
            isfile = False
        else:
            files = [pathname]
            isfile = True

        # Now go through and get timestamps etc..
        for file in sorted(files):
            # Strip path so that we just have the filename.
            movie_folder, movie_filename = os.path.split(file)

            # And now get the timestamp of the filename.
            filename_timestamp = movie_filename.rsplit('-', 1)[0]

            movie_file_list = folder_list.get(movie_folder, {})

            # Check if we already processed this timestamp.
            if movie_file_list.get(filename_timestamp) is not None:
                # Already processed this timestamp, moving on.
                continue

            video_info = {
                'front_camera': {
                    'filename': None,
                    'duration': None,
                    'timestamp': None,
                },
                'left_camera': {
                    'filename': None,
                    'duration': None,
                    'timestamp': None,
                },
                'right_camera': {
                    'filename': None,
                    'duration': None,
                    'timestamp': None,
                },
            }

            if video_settings['video_layout'].front:
                front_filename = str(filename_timestamp) + '-front.mp4'
                front_path = os.path.join(movie_folder, front_filename)
            else:
                front_filename = None
                front_path = ""

            if video_settings['video_layout'].left:
                left_filename = str(filename_timestamp) + '-left_repeater.mp4'
                left_path = os.path.join(movie_folder, left_filename)
            else:
                left_filename = None
                left_path = ""

            if video_settings['video_layout'].right:
                right_filename = str(filename_timestamp) + '-right_repeater.mp4'
                right_path = os.path.join(movie_folder, right_filename)
            else:
                right_filename = None
                right_path = ""

            # Confirm we have at least one movie file:
            if not os.path.isfile(front_path) and \
                    not os.path.isfile(left_path) and \
                    not os.path.isfile(right_path):
                continue

            # Get meta data for each video to determine creation time and duration.
            metadata = get_metadata(video_settings['ffmpeg_exec'], [
                front_path,
                left_path,
                right_path,
            ])

            # Move on to next one if nothing received.
            if not metadata:
                continue

            # Get the longest duration:
            duration = 0
            video_timestamp = None
            for item in metadata:
                _, filename = os.path.split(item['filename'])
                if filename == front_filename:
                    camera = 'front_camera'
                    video_filename = front_filename
                elif filename == left_filename:
                    camera = 'left_camera'
                    video_filename = left_filename
                elif filename == right_filename:
                    camera = 'right_camera'
                    video_filename = right_filename
                else:
                    continue

                # Store duration and timestamp
                video_info[camera].update(filename=video_filename,
                                          duration=item['duration'],
                                          timestamp=item['timestamp'],
                                          )

                # Figure out which one has the longest duration
                duration = item['duration'] if item['duration'] > duration else \
                    duration

                # Figure out starting timestamp
                if video_timestamp is None:
                    video_timestamp = item['timestamp']
                else:
                    video_timestamp = item['timestamp'] \
                        if item['timestamp'] < video_timestamp else \
                        video_timestamp

            if video_timestamp is None:
                # Firmware version 2019.16 changed filename timestamp format.
                if len(filename_timestamp) == 16:
                    # This is for before version 2019.16
                    video_timestamp = datetime.strptime(
                        filename_timestamp,
                        "%Y-%m-%d_%H-%M")
                else:
                    # This is for version 2019.16 and later
                    video_timestamp = datetime.strptime(
                        filename_timestamp,
                        "%Y-%m-%d_%H-%M-%S")

            movie_info = {
                'movie_folder': movie_folder,
                'timestamp': video_timestamp,
                'duration': duration,
                'video_info': video_info,
                'file_only': isfile,
            }

            movie_file_list.update({filename_timestamp: movie_info})
            folder_list.update({movie_folder: movie_file_list})

    return folder_list


def get_metadata(ffmpeg, filenames):
    """ Retrieve the meta data for the clip (i.e. timestamp, duration) """
    # Get meta data for each video to determine creation time and duration.
    ffmpeg_command = [
        ffmpeg,
    ]

    for file in filenames:
        if os.path.isfile(file):
            ffmpeg_command.append('-i')
            ffmpeg_command.append(file)

    ffmpeg_command.append('-hide_banner')

    command_result = run(ffmpeg_command, capture_output=True, text=True)
    input_counter = 0
    file = ''
    metadata = []
    video_timestamp = None
    wait_for_input_line = True
    for line in command_result.stderr.splitlines():
        if search("^Input #", line) is not None:
            file = filenames[input_counter]
            input_counter += 1
            video_timestamp = None
            wait_for_input_line = False
            continue

        if wait_for_input_line:
            continue

        if search("^ *creation_time ", line) is not None:
            line_split = line.split(':', 1)
            video_timestamp = datetime.strptime(line_split[1].strip(),
                                                "%Y-%m-%dT%H:%M:%S.%f%z")
            continue

        if search("^ *Duration: ", line) is not None:
            line_split = line.split(',')
            line_split = line_split[0].split(':', 1)
            duration_list = line_split[1].split(':')
            duration = int(duration_list[0]) * 60 * 60 + \
                int(duration_list[1]) * 60 + \
                int(duration_list[2].split('.')[0]) + \
                (float(duration_list[2].split('.')[1]) / 100)

            # Only add if duration is greater then 0; otherwise ignore.
            if duration <= 0:
                continue

            metadata.append(
                {
                    'filename': file,
                    'timestamp': video_timestamp,
                    'duration': duration,
                }
            )
            continue

    return metadata


def create_intermediate_movie(filename_timestamp,
                              video,
                              video_settings,
                              clip_number,
                              total_clips):
    """ Create intermediate movie files. This is the merging of the 3 camera

    video files into 1 video file. """
    # We first stack (combine the 3 different camera video files into 1
    # and then we concatenate.
    camera_1 = None
    if video['video_info']['front_camera']['filename'] is not None:
        camera_1 = os.path.join(
            video['movie_folder'],
            video['video_info']['front_camera']['filename'])

    left_camera = None
    if video['video_info']['left_camera']['filename'] is not None:
        left_camera = os.path.join(
            video['movie_folder'],
            video['video_info']['left_camera']['filename'])

    right_camera = None
    if video['video_info']['right_camera']['filename'] is not None:
        right_camera = os.path.join(
            video['movie_folder'],
            video['video_info']['right_camera']['filename'])

    if camera_1 is None and left_camera is None and right_camera is None:
        print("\t\tNo valid video files for {timestamp}".format(
            timestamp=filename_timestamp,
        ))
        return None

    if video_settings['video_layout'].swap_left_right:
        camera_2 = left_camera
        clip_2 = (video_settings['video_layout'].left_width, video_settings[
            'video_layout'].left_height)
        camera_0 = right_camera
        clip_0 = (video_settings['video_layout'].right_width, video_settings[
            'video_layout'].right_height)
    else:
        camera_0 = left_camera
        clip_0 = (video_settings['video_layout'].left_width, video_settings[
            'video_layout'].left_height)
        camera_2 = right_camera
        clip_2 = (video_settings['video_layout'].right_width, video_settings[
            'video_layout'].right_height)

    temp_movie_name = os.path.join(video_settings['target_folder'],
                                   filename_timestamp) + '.mp4'

    movie_layout = video_settings['movie_layout']
    speed = video_settings['movie_speed']
    # Confirm if files exist, if not replace with nullsrc
    input_count = 0
    if camera_0 is not None and os.path.isfile(camera_0):
        ffmpeg_command_0 = [
            '-i',
            camera_0
        ]
        ffmpeg_camera_0 = '[0:v] ' + video_settings['input_0']
        input_count += 1
    else:
        ffmpeg_command_0 = []
        ffmpeg_camera_0 = video_settings['background'].format(
            duration=video['duration'],
            speed=speed,
            width=clip_0[0],
            height=clip_0[1],
        ) + '[left];'

    if camera_1 is not None and os.path.isfile(camera_1):
        ffmpeg_command_1 = [
            '-i',
            camera_1
        ]
        ffmpeg_camera_1 = '[' + str(input_count) + ':v] ' + \
                          video_settings['input_1']
        input_count += 1
    else:
        ffmpeg_command_1 = []
        ffmpeg_camera_1 = video_settings['background'].format(
            duration=video['duration'],
            speed=speed,
            width=video_settings['video_layout'].front_width,
            height=video_settings['video_layout'].front_height,
        ) + '[front];'

    if camera_2 is not None and os.path.isfile(camera_2):
        ffmpeg_command_2 = [
            '-i',
            camera_2
        ]
        ffmpeg_camera_2 = '[' + str(input_count) + ':v] ' + \
                          video_settings['input_2']
        input_count += 1
    else:
        ffmpeg_command_2 = []
        ffmpeg_camera_2 = video_settings['background'].format(
            duration=video['duration'],
            speed=speed,
            width=clip_2[0],
            height=clip_2[1],
        ) + '[right];'

    # If we could not get a timestamp then retrieve it from the filename
    # instead
    if video['timestamp'] is None:
        # Get the pure filename which would be timestamp in format:
        # YYYY-MM-DD_HH-MM
        # Split in date and time parts
        timestamps = filename_timestamp.split('_')
        # Split date
        date = timestamps[0].split('-')
        # Split time
        time = timestamps[1].split('-')
        video_timestamp = datetime(int(date[0]),
                                   int(date[1]),
                                   int(date[2]),
                                   int(time[0]),
                                   int(time[1]))
    else:
        video_timestamp = video['timestamp']

    local_timestamp = video_timestamp.astimezone(get_localzone())

    print("\t\tProcessing clip {clip_number}/{total_clips} from {timestamp} "
          "and {duration} seconds long.".format(
              clip_number=clip_number + 1,
              total_clips=total_clips,
              timestamp=local_timestamp.strftime("%x %X"),
              duration=int(video['duration']),
          ))

    epoch_timestamp = int(video_timestamp.timestamp())

    ffmpeg_filter = \
        video_settings['base'].format(
            duration=video['duration'],
            speed=speed, ) + \
        ffmpeg_camera_0 + \
        ffmpeg_camera_1 + \
        ffmpeg_camera_2 + \
        video_settings['clip_positions'] + \
        video_settings['timestamp_text'].format(
            epoch_time=epoch_timestamp) + \
        video_settings['ffmpeg_speed']

    ffmpeg_command = [video_settings['ffmpeg_exec']] + \
        ffmpeg_command_0 + \
        ffmpeg_command_1 + \
        ffmpeg_command_2 + \
        ['-filter_complex', ffmpeg_filter] + \
        video_settings['other_params']

    ffmpeg_command = ffmpeg_command + ['-y', temp_movie_name]
    # print(ffmpeg_command)
    # Run the command.
    try:
        run(ffmpeg_command, capture_output=True, check=True)
    except CalledProcessError as exc:
        print("\t\t\tError trying to create clip for {base_name}. RC: {rc}\n"
              "\t\t\tCommand: {command}\n"
              "\t\t\tError: {stderr}\n\n".format(
                  base_name=os.path.join(video['movie_folder'],
                                         filename_timestamp),
                  rc=exc.returncode,
                  command=exc.cmd,
                  stderr=exc.stderr,
              ))
        return None

    return temp_movie_name


def create_movie(clips_list, movie_filename, video_settings):
    """ Concatenate provided movie files into 1."""
    # Just return if there are no clips.
    if not clips_list:
        return None

    # If there is only 1 clip then we can just put it in place as there is
    # nothing to concatenate.
    if len(clips_list) == 1:
        # If not output folder provided then these 2 are the same and thus
        # nothing to be done.
        if movie_filename == clips_list[0]['video_filename']:
            return movie_filename

        # There really was only one, no need to create, just move
        # intermediate file.
        # Remove file 1st if it exist otherwise on Windows we can't rename.
        if os.path.isfile(movie_filename):
            try:
                os.remove(movie_filename)
            except OSError as exc:
                # Putting out error but going to try to copy/move anyway.
                print("\t\tError trying to remove file {}: {}".format(
                    movie_filename,
                    exc))

        if not video_settings['keep_intermediate']:
            try:
                shutil.move(clips_list[0]['video_filename'],
                            movie_filename)
            except OSError as exc:
                print("\t\tError trying to move file {} to {}: {}".format(
                    clips_list[0]['video_filename'],
                    movie_filename,
                    exc))
                return None
        else:
            try:
                shutil.copyfile(clips_list[0]['video_filename'],
                                movie_filename)
            except OSError as exc:
                print("\t\tError trying to copy file {} to {}: {}".format(
                    clips_list[0]['video_filename'],
                    movie_filename,
                    exc))
                return None

        return movie_filename

    # Go through the list of clips to create the command.
    ffmpeg_concat_input = []
    concat_filter_complex = ''
    total_clips = 0
    # Loop through the list sorted by video timestamp.
    for video_clip in sorted(clips_list, key=lambda video: video[
        'video_timestamp']):
        if not os.path.isfile(video_clip['video_filename']):
            print("\t\tFile {} does not exist anymore, skipping.".format(
                video_clip['video_filename']
            ))
            continue

        ffmpeg_concat_input = ffmpeg_concat_input + ['-i',
            video_clip['video_filename']]
        concat_filter_complex = concat_filter_complex + \
            '[{clip}:v:0] '.format(
                clip=total_clips
            )
        total_clips = total_clips + 1

    if total_clips == 0:
        print("\t\tError: No valid clips to merge found.")
        return None

    concat_filter_complex = concat_filter_complex + \
        "concat=n={total_clips}:v=1:a=0 [v]".format(
            total_clips=total_clips,
        )

    ffmpeg_params = ['-filter_complex',
                     concat_filter_complex,
                     '-map',
                     '[v]',
                     '-preset',
                     video_settings['movie_compression'],
                     '-crf',
                     MOVIE_QUALITY[video_settings['movie_quality']]
                     ] + \
        video_settings['video_encoding']

    ffmpeg_command = [video_settings['ffmpeg_exec']] + \
        ffmpeg_concat_input + \
        ffmpeg_params + \
        ['-y', movie_filename]

    try:
        run(ffmpeg_command, capture_output=True, check=True)
    except CalledProcessError as exc:
        print("\t\tError trying to create movie {base_name}. RC: {rc}\n"
              "\t\tCommand: {command}\n"
              "\t\tError: {stderr}\n\n".format(
                  base_name=movie_filename,
                  rc=exc.returncode,
                  command=exc.cmd,
                  stderr=exc.stderr,
              ))
        return None

    return movie_filename


def delete_intermediate(movie_files):
    """ Delete the files provided in list """
    for file in movie_files:
        if file is not None:
            if os.path.isfile(file):
                try:

                    os.remove(file)
                except OSError as exc:
                    print("\t\tError trying to remove file {}: {}".format(
                        file,
                        exc))
            elif os.path.isdir(file):
                try:

                    os.rmdir(file)
                except OSError as exc:
                    print("\t\tError trying to remove folder {}: {}".format(
                        file,
                        exc))


def process_folders(folders, video_settings, skip_existing, delete_source):
    """ Process all clips found within folders. """
    start_time = timestamp()

    total_clips = 0
    for folder_number, folder_name in enumerate(sorted(folders)):
        total_clips = total_clips + len(folders[folder_name])
    print("Discovered {total_folders} folders with {total_clips} clips to "
          "process.".format(
              total_folders=len(folders),
              total_clips=total_clips
          ))

    # Loop through all the folders.
    dashcam_clips = []
    for folder_number, folder_name in enumerate(sorted(folders)):
        files = folders[folder_name]

        # Ensure the clips are sorted based on video timestamp.
        sorted_video_clips = sorted(
            files,
            key=lambda video: files[video]['timestamp'])

        # Get the start and ending timestamps, we add duration to
        # last timestamp to get true ending.
        first_clip_tmstp = files[sorted_video_clips[0]]['timestamp']

        last_clip_tmstp  = files[sorted_video_clips[-1]]['timestamp'] + \
                                 timedelta(
                                     seconds=
                                     files[sorted_video_clips[-1]]['duration'])

        # Convert timestamp to local timezone.
        first_clip_tmstp = first_clip_tmstp.astimezone(get_localzone())
        last_clip_tmstp = last_clip_tmstp.astimezone(get_localzone())

        # Put them together to create the filename for the folder.
        movie_filename = first_clip_tmstp.strftime("%Y-%m-%dT%H-%M-%S") + \
            "_" + last_clip_tmstp.strftime("%Y-%m-%dT%H-%M-%S")

        # Now add full path to it.
        movie_filename = os.path.join(video_settings['target_folder'],
                                      movie_filename) + '.mp4'

        # Do not process the files from this folder if we're to skip it if
        # the target movie file already exist.
        if skip_existing and os.path.isfile(movie_filename):
            print("\tSkipping folder {folder} as {filename} is already "
                  "created ({folder_number}/{total_folders})".format(
                      folder=folder_name,
                      filename=movie_filename,
                      folder_number=folder_number + 1,
                      total_folders=len(folders),
                  ))
            continue

        print("\tProcessing {total_clips} clips in folder {folder} "
              "({folder_number}/{total_folders})".format(
                  total_clips=len(files),
                  folder=folder_name,
                  folder_number=folder_number + 1,
                  total_folders=len(folders),
              ))

        # Loop through all the files within the folder.
        folder_clips = []
        delete_folder_clips = []
        delete_folder_files = delete_source
        delete_file_list = []
        folder_timestamp = None

        for clip_number, filename_timestamp in enumerate(sorted_video_clips):
            video_timestamp_info = files[filename_timestamp]
            folder_timestamp = video_timestamp_info['timestamp'] \
                if folder_timestamp is None else folder_timestamp
            clip_name = create_intermediate_movie(
                filename_timestamp,
                video_timestamp_info,
                video_settings,
                clip_number,
                len(files)
            )

            if clip_name is not None:
                if video_timestamp_info['file_only']:
                    # When file only there is no concatenation at the folder
                    # level, will only happen at the higher level if requested.
                    dashcam_clips.append({
                        'video_timestamp': video_timestamp_info['timestamp'],
                        'video_filename': clip_name
                    })
                else:
                    # Movie was created, store name for concatenation.
                    folder_clips.append({
                        'video_timestamp': video_timestamp_info['timestamp'],
                        'video_filename': clip_name
                    })

                    # Add clip for deletion only if it's name is not the
                    # same as the resulting movie filename
                    if clip_name != movie_filename:
                        delete_folder_clips.append(clip_name)

                    # Add the files to our list for removal.
                    video_info = video_timestamp_info['video_info']
                    if video_info['front_camera']['filename'] is not None:
                        delete_file_list.append(
                            os.path.join(
                                video_timestamp_info['movie_folder'],
                                video_info['front_camera']['filename']))

                    if video_info['left_camera']['filename'] is not None:
                        delete_file_list.append(
                            os.path.join(
                                video_timestamp_info['movie_folder'],
                                video_info['left_camera']['filename']))

                    if video_info['right_camera']['filename'] is not None:
                        delete_file_list.append(
                            os.path.join(
                                video_timestamp_info['movie_folder'],
                                video_info['right_camera']['filename']))
            else:
                delete_folder_files = False

        # All clips in folder have been processed, merge those clips
        # together now.
        movie_name = None
        if folder_clips:
            print("\t\tCreating movie {}, please be patient.".format(
                movie_filename))

            movie_name = create_movie(
                folder_clips,
                movie_filename,
                video_settings,
            )

        # Add this one to our list for final concatenation
        if movie_name is not None:
            dashcam_clips.append({
                'video_timestamp': folder_timestamp,
                'video_filename': movie_name
            })
            # Delete the intermediate files we created.
            if not video_settings['keep_intermediate']:
                delete_intermediate(delete_folder_clips)

            # Delete the source files if stated to delete.
            if delete_folder_files:
                print("\t\tDeleting files and folder {folder_name}".format(
                    folder_name=folder_name
                ))
                delete_intermediate(delete_file_list)
                # And delete the folder
                delete_intermediate([folder_name])

            print("\tMovie {base_name} for folder {folder_name} is "
                  "ready.".format(
                      base_name=movie_name,
                      folder_name=folder_name,
                  ))

    # Now that we have gone through all the folders merge.
    # We only do this if merge is enabled OR if we only have 1 clip and for
    # output a specific filename was provided.
    movie_name = None
    if dashcam_clips:
        if video_settings['merge_subdirs'] or \
           (len(folders) == 1 and
            video_settings['target_filename'] is not None):

            if video_settings['movie_filename'] is not None:
                movie_filename = video_settings['movie_filename']
            elif video_settings['target_filename'] is not None:
                movie_filename = video_settings['target_filename']
            else:
                folder, movie_filename = os.path.split(
                    video_settings['target_folder'])
                # If there was a trailing separator provided then it will be
                # empty, redo split then.
                if movie_filename == '':
                    movie_filename = os.path.split(folder)[1]

            movie_filename = os.path.join(
                video_settings['target_folder'],
                movie_filename
            )

            # Make sure it ends in .mp4
            if os.path.splitext(movie_filename)[1] != '.mp4':
                movie_filename = movie_filename + '.mp4'

            print("\tCreating movie {}, please be patient.".format(
                movie_filename))

            movie_name = create_movie(
                dashcam_clips,
                movie_filename,
                video_settings,
            )

        if movie_name is not None:
            print("Movie {base_name} has been created, enjoy.".format(
                base_name=movie_name))
        else:
            print("All folders have been processed, resulting movie files are "
                  "located in {target_folder}".format(
                      target_folder=video_settings['target_folder']
                  ))
    else:
        print("No clips found.")

    end_time = timestamp()
    real = int((end_time - start_time))

    print("Total processing time: {real}".format(
        real=str(timedelta(seconds=real)),
    ))
    if video_settings['notification']:
        if movie_name is not None:
            notify("TeslaCam", "Completed",
                   "{total_folders} folder{folders} with {total_clips} "
                   "clip{clips} have been processed, movie {movie_name} has "
                   "been created.".format(
                       folders='' if len(folders) < 2 else 's',
                       total_folders=len(folders),
                       clips='' if total_clips < 2 else 's',
                       total_clips=total_clips,
                       movie_name=video_settings['target_folder']
                   ))
        else:
            notify("TeslaCam", "Completed",
                   "{total_folders} folder{folders} with {total_clips} "
                   "clip{clips} have been processed, {target_folder} contains "
                   "resulting files.".format(
                       folders='' if len(folders) < 2 else 's',
                       total_folders=len(folders),
                       clips='' if total_clips < 2 else 's',
                       total_clips=total_clips,
                       target_folder=video_settings['target_folder']
                   ))
    print()


def resource_path(relative_path):
    """ Return absolute path for provided relative item based on location

    of program.
    """
    # If compiled with pyinstaller then sys._MEIPASS points to the location
    # of the bundle. Otherwise path of python script is used.
    base_path = getattr(sys, '_MEIPASS', str(Path(__file__).parent))
    return os.path.join(base_path, relative_path)


def notify_macos(title, subtitle, message):
    """ Notification on MacOS """
    try:
        run(['osascript',
             '-e display notification "{message}" with title "{title}" '
             'subtitle "{subtitle}"'
             ''.format(
                 message=message,
                 title=title,
                 subtitle=subtitle,
             )])
    except Exception as exc:
        print("Failed in notifification: ", exc)


def notify_windows(title, subtitle, message):
    """ Notification on Windows """
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(
            threaded=True,
            title="{} {}".format(title, subtitle),
            msg=message,
            duration=5,
            icon_path=resource_path("tesla_dashcam.ico")
        )

        run(['notify-send',
             '"{title} {subtitle}"'.format(
                 title=title,
                 subtitle=subtitle),
             '"{}"'.format(message),
             ])
    except Exception:
        pass


def notify_linux(title, subtitle, message):
    """ Notification on Linux """
    try:
        run(['notify-send',
             '"{title} {subtitle}"'.format(
                 title=title,
                 subtitle=subtitle),
             '"{}"'.format(message),
             ])
    except Exception as exc:
        print("Failed in notifification: ", exc)


def notify(title, subtitle, message):
    """ Call function to send notification based on OS """
    if sys.platform == 'darwin':
        notify_macos(title, subtitle, message)
    elif sys.platform == 'win32':
        notify_windows(title, subtitle, message)
    elif sys.platform == 'linux':
        notify_linux(title, subtitle, message)


def main() -> None:
    """ Main function """

    internal_ffmpeg = getattr(sys, 'frozen', None) is not None
    ffmpeg_default = resource_path(FFMPEG.get(sys.platform, 'ffmpeg'))

    movie_folder = os.path.join(str(Path.home()),
                                MOVIE_HOMEDIR.get(sys.platform),'')


    # Check if ffmpeg exist, if not then hope it is in default path or
    # provided.
    if not os.path.isfile(ffmpeg_default):
        internal_ffmpeg = False
        ffmpeg_default = FFMPEG.get(sys.platform, 'ffmpeg')

    epilog = "This program leverages ffmpeg which is included. See " \
             "https://ffmpeg.org/ for more information on ffmpeg" if \
        internal_ffmpeg else 'This program requires ffmpeg which can be ' \
                             'downloaded from: ' \
                             'https://ffmpeg.org/download.html'

    parser = MyArgumentParser(
        description='tesla_dashcam - Tesla DashCam & Sentry Video Creator',
        epilog=epilog,
        formatter_class=SmartFormatter,
        fromfile_prefix_chars='@',
    )

    parser.add_argument('--version',
                        action='version',
                        version=' %(prog)s ' + VERSION_STR
                        )
    parser.add_argument('source',
                        type=str,
                        nargs='*',
                        help="Folder(s) containing the saved camera "
                             "files. Filenames can be provided as well to "
                             "manage individual clips."
                        )

    sub_dirs = parser.add_mutually_exclusive_group()
    sub_dirs.add_argument('--exclude_subdirs',
                          dest='exclude_subdirs',
                          action='store_true',
                          help="Do not search all sub folders for video files "
                               "to."
                          )

    sub_dirs.add_argument('--merge',
                          dest='merge_subdirs',
                          action='store_true',
                          help="Merge the video files from different "
                               "folders into 1 big video file."
                          )

    parser.add_argument('--output',
                        required=False,
                        default = movie_folder,
                        type=str,
                        help="R|Path/Filename for the new movie file. "
                             "Intermediate files will be stored in same "
                             "folder.\n"
                        )

    parser.add_argument('--keep-intermediate',
                        dest='keep_intermediate',
                        action='store_true',
                        help='Do not remove the intermediate video files that '
                             'are created')

    parser.add_argument('--delete_source',
                        dest='delete_source',
                        action='store_true',
                        help='Delete the processed files on the '
                        'TeslaCam drive.'
                        )

    parser.add_argument('--no-notification',
                        dest='system_notification',
                        action='store_false',
                        help='Do not create a notification upon '
                             'completion.')

    parser.add_argument('--layout',
                        required=False,
                        choices=['WIDESCREEN',
                                 'FULLSCREEN',
                                 'PERSPECTIVE', ],
                        default='FULLSCREEN',
                        help="R|Layout of the created video.\n"
                             "    FULLSCREEN: Front camera center top, "
                             "side cameras underneath it.\n"
                             "    WIDESCREEN: Output from all 3 cameras are "
                             "next to each other.\n"
                             "    PERSPECTIVE: Front camera center top, "
                             "side cameras next to it in perspective.\n"
                        )
    parser.add_argument('--scale',
                        dest='clip_scale',
                        type=float,
                        help="R|Set camera clip scale, scale of 1 "
                             "is 1280x960 camera clip. "
                             "Defaults:\n"
                             "    WIDESCREEN: 1/2 (640x480, video is "
                             "1920x480)\n"
                             "    FULLSCREEN: 1/2 (640x480, video is "
                             "1280x960)\n"                             
                             "    PERSPECTIVE: 1/4 (320x240, video is "
                             "980x380)\n"
                        )

    mirror_or_rear = parser.add_mutually_exclusive_group()

    mirror_or_rear.add_argument('--mirror',
                                dest='mirror',
                                action='store_true',
                                help="Video from side cameras as if being "
                                     "viewed through the sidemirrors. Cannot "
                                     "be used in combination with --rear."
                                )
    mirror_or_rear.add_argument('--rear',
                                dest='rear',
                                action='store_true',
                                help="Video from side cameras as if looking "
                                     "backwards. Cannot be used in "
                                     "combination with --mirror."
                                )
    parser.set_defaults(mirror=True)
    parser.set_defaults(rear=False)

    swap_cameras = parser.add_mutually_exclusive_group()
    swap_cameras.add_argument('--swap',
                              dest='swap',
                              action='store_const',
                              const=1,
                              help="Swap left and right cameras, default when "
                                   "layout FULLSCREEN with --rear option is "
                                   "chosen."
                              )
    swap_cameras.add_argument('--no-swap',
                              dest='swap',
                              action='store_const',
                              const=0,
                              help="Do not swap left and right cameras, "
                                   "default with all other options."
                              )

    # camera_group = parser.add_argument_group(title='Camera Exclusion',
    #                                          description="Exclude "
    #                                                      "one or "
    #                                                      "more "
    #                                                      "cameras:")
    # camera_group.add_argument('--no-front',
    #                           dest='no_front',
    #                           action='store_true',
    #                           help="Exclude front camera from video.")
    # camera_group.add_argument('--no-left',
    #                           dest='no_left',
    #                           action='store_true',
    #                           help="Exclude left camera from video.")
    # camera_group.add_argument('--no-right',
    #                           dest='no_right',
    #                           action='store_true',
    #                           help="Exclude right camera from video.")

    speed_group = parser.add_mutually_exclusive_group()
    speed_group.add_argument('--slowdown',
                             dest='slow_down',
                             type=int,
                             help="Slow down video output. Accepts a number "
                                  "that is then used as multiplier, "
                                  "providing 2 means half the speed."
                             )
    swap_cameras.add_argument('--speedup',
                              dest='speed_up',
                              type=int,
                              help="Speed up the video. Accepts a number "
                                   "that is then used as a multiplier, "
                                   "providing 2 means twice the speed."
                              )

    encoding_group = parser.add_mutually_exclusive_group()
    encoding_group.add_argument('--encoding',
                                required=False,
                                choices=['x264',
                                         'x265', ],
                                default='x264',
                                help="R|Encoding to use for video creation.\n"
                                     "    x264: standard encoding, can be "
                                     "viewed on most devices but results in "
                                     "bigger file.\n"
                                     "    x265: newer encoding standard but "
                                     "not all devices support this yet.\n"
                                )
    encoding_group.add_argument('--enc',
                                required=False,
                                type=str,
                                help="R|Provide a custom encoding for video "
                                     "creation.\n"
                                     "Note: when using this option the --gpu "
                                     "option is ignored. To use GPU hardware "
                                     "acceleration specify a encoding that "
                                     "provides this."
                                )

    gpu_help = "R|Use GPU acceleration, only enable if " \
               "supported by hardware.\n" \
               " MAC: All MACs with Haswell CPU or later  " \
               "support this (Macs after 2013).\n" \
               "      See following link as well: \n" \
               "         https://en.wikipedia.org/wiki/List_of_" \
               "Macintosh_models_grouped_by_CPU_type#Haswell\n" \
               " Windows and Linux: PCs with NVIDIA graphic " \
               "cards support this as well.\n" \
               "                    For more information on " \
               "supported cards see:\n" \
               "         https://developer.nvidia.com/" \
               "video-encode-decode-gpu-support-matrix"

    if sys.platform == 'darwin':
        parser.add_argument('--no-gpu',
                            dest='gpu',
                            action='store_true',
                            help=gpu_help
                            )
    else:
        parser.add_argument('--gpu',
                            dest='gpu',
                            action='store_true',
                            help=gpu_help
                            )

    timestamp_group = parser.add_argument_group(title='Timestamp',
                                                description="Options for "
                                                            "timestamp:")
    timestamp_group.add_argument('--no-timestamp',
                                 dest='no_timestamp',
                                 action='store_true',
                                 help="Include timestamp in video")

    timestamp_group.add_argument('--halign',
                                 required=False,
                                 choices=['LEFT',
                                          'CENTER',
                                          'RIGHT', ],
                                 default='CENTER',
                                 help='Horizontal alignment for timestamp')

    timestamp_group.add_argument('--valign',
                                 required=False,
                                 choices=['TOP',
                                          'MIDDLE',
                                          'BOTTOM', ],
                                 default='BOTTOM',
                                 help='Vertical Alignment for timestamp')

    timestamp_group.add_argument('--font',
                                 required=False,
                                 type=str,
                                 default=DEFAULT_FONT.get(sys.platform, None),
                                 help="Fully qualified filename (.ttf) to the "
                                      "font to be chosen for timestamp."
                                 )

    timestamp_group.add_argument('--fontsize',
                                 required=False,
                                 type=int,
                                 help="Font size for timestamp. Default is "
                                      "scaled based on video scaling.")

    timestamp_group.add_argument('--fontcolor',
                                 required=False,
                                 type=str,
                                 default='white',
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
                                      "Color"
                                 )

    quality_group = parser.add_argument_group(title='Video Quality',
                                              description="Options for "
                                                          "resulting video "
                                                          "quality and size:"
                                              )

    quality_group.add_argument('--quality',
                               required=False,
                               choices=['LOWEST',
                                        'LOWER',
                                        'LOW',
                                        'MEDIUM',
                                        'HIGH'],
                               default='LOWER',
                               help="Define the quality setting for the "
                                    "video, higher quality means bigger file "
                                    "size but might not be noticeable."
                               )

    quality_group.add_argument('--compression',
                               required=False,
                               choices=['ultrafast',
                                        'superfast',
                                        'veryfast',
                                        'faster',
                                        'fast',
                                        'medium',
                                        'slow',
                                        'slower',
                                        'veryslow'],
                               default='medium',
                               help="Speed to optimize video. Faster speed "
                                    "results in a bigger file. This does not "
                                    "impact the quality of the video, "
                                    "just how "
                                    "much time is used to compress it."
                               )

    if internal_ffmpeg:
        parser.add_argument('--ffmpeg',
                            required=False,
                            type=str,
                            help='Full path and filename for alternative '
                                 'ffmpeg.')
    else:
        parser.add_argument('--ffmpeg',
                            required=False,
                            type=str,
                            default=ffmpeg_default,
                            help='Path and filename for ffmpeg. Specify if '
                                 'ffmpeg is not within path.')

    monitor_group = parser.add_argument_group(
        title="Monitor for TeslaDash Cam drive",
        description="Parameters to monitor for a drive to be attached with "
                    "folder TeslaCam in the root."
    )

    monitor_group.add_argument('--monitor',
                               dest='monitor',
                               action='store_true',
                               help='Enable monitoring for drive to be '
                                    'attached with TeslaCam folder.'
                               )

    monitor_group.add_argument('--monitor_once',
                               dest='monitor_once',
                               action='store_true',
                               help='Enable monitoring and exit once drive '
                                    'with TeslaCam folder has been attached '
                                    'and files processed.'
                               )

    update_check_group = parser.add_argument_group(
        title="Update Check",
        description="Check for updates"
    )

    update_check_group.add_argument('--check_for_update',
                                    dest='check_for_updates',
                                    action='store_true',
                                    help='Check for updates, do not do '
                                         'anything else.'
                                    )

    update_check_group.add_argument('--no-check_for_update',
                                    dest='no_check_for_updates',
                                    action='store_true',
                                    help='A check for new updates is '
                                         'performed every time. With this '
                                         'parameter that can be disabled'
                                    )

    update_check_group.add_argument('--include_test',
                                    dest='include_beta',
                                    action='store_true',
                                    help='Include test (beta) releases '
                                         'when checking for updates.'
                                    )

    args = parser.parse_args()

    if not args.no_check_for_updates or args.check_for_updates:
        release_info = check_latest_release(args.include_beta)
        if release_info is not None:
            new_version = False
            if release_info.get('tag_name') is not None:
                github_version = release_info.get('tag_name').split('.')
                if len(github_version) == 3:
                    # Release tags normally start with v. If that is the case
                    # then strip the v.
                    try:
                        major_version = int(github_version[0])
                    except ValueError:
                        major_version = int(github_version[0][1:])

                    minor_version = int(github_version[1])
                    if release_info.get('prerelease'):
                        # Drafts will have b and then beta number.
                        patch_version = int(github_version[2].split('b')[0])
                        beta_version = int(github_version[2].split('b')[1])
                    else:
                        patch_version = int(github_version[2])
                        beta_version = -1

                    if major_version == VERSION['major']:
                        if minor_version == VERSION['minor']:
                            if patch_version == VERSION['patch']:
                                if beta_version > VERSION['beta'] or \
                                        (beta_version == -1 and
                                         VERSION['beta'] != -1):
                                    new_version = True
                            elif patch_version > VERSION['patch']:
                                new_version = True
                        elif minor_version > VERSION['minor']:
                            new_version = True
                    elif major_version > VERSION['major']:
                        new_version = True

            if new_version:
                beta = ""
                if release_info.get('prerelease'):
                    beta = "beta "

                release_notes = ""
                if not args.check_for_updates:
                    if args.system_notification:
                        notify("TeslaCam", "Update available",
                               "New {beta}release {release} is available. You are "
                               "on version {version}".format(
                                   beta=beta,
                                   release=release_info.get('tag_name'),
                                   version=VERSION_STR,
                               ))
                    release_notes = "Use --check-for-update to get latest " \
                                    "release notes."

                print("New {beta}release {release} is available for download "
                      "({url}). You are currently on {version}. {rel_note}".format(
                          beta=beta,
                          release=release_info.get('tag_name'),
                          url=release_info.get('html_url'),
                          version=VERSION_STR,
                          rel_note=release_notes,
                      ))

                if args.check_for_updates:
                    print("You can download the new release from: {url}".format(
                        url=release_info.get('html_url')
                    ))
                    print("Release Notes:\n {release_notes}".format(
                        release_notes=release_info.get('body')
                    ))
                    return
            else:
                if args.check_for_updates:
                    print("{version} is the latest release available.".format(
                        version=VERSION_STR,
                    ))
                    return
        else:
            print("Did not retrieve latest version info.")

    ffmpeg = ffmpeg_default if getattr(args, 'ffmpeg', None) is None else \
        args.ffmpeg

    mirror_sides = ''
    if args.rear:
        side_camera_as_mirror = False
    else:
        side_camera_as_mirror = True

    if side_camera_as_mirror:
        mirror_sides = ', hflip'

    black_base = 'color=duration={duration}:'
    black_size = 's={width}x{height}:c=black '

    if args.layout == 'WIDESCREEN':
        layout_settings = WideScreen()
    elif args.layout == 'FULLSCREEN':
        layout_settings = FullScreen()
    elif args.layout == 'PERSPECTIVE':
        layout_settings = Perspective()
    else:
        layout_settings = Diagonal()

    if args.clip_scale is not None and args.clip_scale > 0:
        layout_settings.scale = args.clip_scale

    # This portion is not ready yet, hence is temporary set to true for now.
    # layout_settings.front = not args.no_front
    # layout_settings.left = not args.no_left
    # layout_settings.right = not args.no_right
    layout_settings.front = True
    layout_settings.left = True
    layout_settings.right = True

    ffmpeg_base = black_base + black_size.format(
        width=layout_settings.video_width,
        height=layout_settings.video_height,
    ) + '[base];'

    ffmpeg_black_video = black_base + black_size

    ffmpeg_input_0 = 'setpts=PTS-STARTPTS, ' \
                     'scale={clip_width}x{clip_height} {mirror}{options}' \
                     ' [left];'.format(
                         clip_width=layout_settings.left_width,
                         clip_height=layout_settings.left_height,
                         mirror=mirror_sides,
                         options=layout_settings.left_options,
                     )

    ffmpeg_input_1 = 'setpts=PTS-STARTPTS, ' \
                     'scale={clip_width}x{clip_height} {options}' \
                     ' [front];'.format(
                         clip_width=layout_settings.front_width,
                         clip_height=layout_settings.front_height,
                         options=layout_settings.front_options,
                     )

    ffmpeg_input_2 = 'setpts=PTS-STARTPTS, ' \
                     'scale={clip_width}x{clip_height} {mirror}{options}' \
                     ' [right];'.format(
                         clip_width=layout_settings.right_width,
                         clip_height=layout_settings.right_height,
                         mirror=mirror_sides,
                         options=layout_settings.right_options,
                     )

    ffmpeg_video_position = \
        '[base][left] overlay=eof_action=pass:repeatlast=0:' \
        'x={left_x}:y={left_y} [left1];' \
        '[left1][front] overlay=eof_action=pass:repeatlast=0:' \
        'x={front_x}:y={front_y} [front1];' \
        '[front1][right] overlay=eof_action=pass:repeatlast=0:' \
        'x={right_x}:y={right_y}'.format(
            left_x=layout_settings.left_x,
            left_y=layout_settings.left_y,
            front_x=layout_settings.front_x,
            front_y=layout_settings.front_y,
            right_x=layout_settings.right_x,
            right_y=layout_settings.right_y,
        )

    filter_counter = 0
    filter_label = '[tmp{filter_counter}];[tmp{filter_counter}] '
    ffmpeg_timestamp = ''
    if not args.no_timestamp:
        if args.font is not None and args.font != '':
            font_file = args.font
        else:
            font_file = DEFAULT_FONT.get(sys.platform, None)

        if font_file is None:
            print("Unable to get a font file. Please provide valid font file.")
            return

        ffmpeg_timestamp = filter_label.format(
            filter_counter=filter_counter) + \
            'drawtext=fontfile={fontfile}:'.format(
                fontfile=font_file,
            )
        filter_counter += 1

        # If fontsize is not provided then scale font size based on scaling
        # of video clips, otherwise use fixed font size.
        if args.fontsize is None or args.fontsize == 0:
            fontsize = 16 * layout_settings.font_scale * \
                       layout_settings.scale
        else:
            fontsize = args.fontsize

        ffmpeg_timestamp = ffmpeg_timestamp + \
            'fontcolor={fontcolor}:fontsize={fontsize}:' \
            'borderw=2:bordercolor=black@1.0:' \
            'x={halign}:y={valign}:'.format(
                fontcolor=args.fontcolor,
                fontsize=fontsize,
                valign=VALIGN[args.valign],
                halign=HALIGN[args.halign],
            )

        ffmpeg_timestamp = ffmpeg_timestamp + \
            "text='%{{pts\:localtime\:{epoch_time}\:%x %X}}'"

    speed = args.slow_down if args.slow_down is not None else ''
    speed = 1 / args.speed_up if args.speed_up is not None else speed
    ffmpeg_speed = ''
    if speed != '':
        ffmpeg_speed = filter_label.format(
            filter_counter=filter_counter) + \
            " setpts={speed}*PTS".format(speed=speed)
        filter_counter += 1

    ffmpeg_params = [
        '-preset',
        args.compression,
        '-crf',
        MOVIE_QUALITY[args.quality]
    ]

    use_gpu = args.gpu
    if sys.platform == 'darwin':
        use_gpu = not args.gpu

    video_encoding = []
    if args.enc is None:
        encoding = args.encoding
        # GPU acceleration enabled
        if use_gpu:
            print("GPU acceleration is enabled")
            if sys.platform == 'darwin':
                video_encoding = video_encoding + \
                    ['-allow_sw',
                     '1'
                     ]
                encoding = encoding + '_mac'
            else:
                encoding = encoding + '_nvidia'

            bit_rate = str(int(10000 * layout_settings.scale)) + 'K'
            video_encoding = video_encoding + \
               ['-b:v',
                bit_rate,
                ]

        video_encoding = video_encoding + \
            ['-c:v',
             MOVIE_ENCODING[encoding]
             ]

    else:
        video_encoding = video_encoding + \
            ['-c:v',
             args.enc
             ]

    ffmpeg_params = ffmpeg_params + video_encoding

    # Determine the target folder and filename.
    # If no extension then assume it is a folder.
    if os.path.splitext(args.output)[1] is None:
        target_folder, target_filename = os.path.split(args.output)
        if target_filename is None:
            # If nothing in target_filename then no folder was given,
            # setting default movie folder
            target_folder = movie_folder
            target_filename = args.output
    else:
        # Folder only provided.
        target_folder = args.output
        target_filename = None

    # Create folder if not already existing.
    if not os.path.isdir(target_folder):
        os.mkdir(target_folder)

    # Determine if left and right cameras should be swapped or not.
    if args.swap is None:
        # Default is set based on layout chosen.
        if args.layout == 'FULLSCREEN':
            # FULLSCREEN is different, if doing mirror then default should
            # not be swapping. If not doing mirror then default should be
            # to swap making it seem more like a "rear" camera.
            layout_settings.swap_left_right = not side_camera_as_mirror
    else:
        layout_settings.swap_left_right = args.swap

    # Set the run type based on arguments.
    runtype = 'RUN'
    if args.monitor:
        runtype = 'MONITOR'
    elif args.monitor_once:
        runtype = 'MONITOR_ONCE'

    # If no source provided then set to MONITOR_ONCE and we're only going to
    # take SavedClips
    source_list = args.source
    if not source_list:
        source_list = ['SavedClips']
        if runtype == 'RUN':
            runtype = 'MONITOR_ONCE'

    video_settings = {
        'source_folder': source_list,
        'output': args.output,
        'target_folder': target_folder,
        'target_filename': target_filename,
        'run_type': runtype,
        'merge_subdirs': args.merge_subdirs,
        'movie_filename': None,
        'keep_intermediate': args.keep_intermediate,
        'notification': args.system_notification,
        'movie_layout': args.layout,
        'movie_speed': speed,
        'video_encoding': video_encoding,
        'movie_encoding': args.encoding,
        'movie_compression': args.compression,
        'movie_quality': args.quality,
        'background': ffmpeg_black_video,
        'ffmpeg_exec': ffmpeg,
        'base': ffmpeg_base,
        'video_layout': layout_settings,
        'clip_positions': ffmpeg_video_position,
        'timestamp_text': ffmpeg_timestamp,
        'ffmpeg_speed': ffmpeg_speed,
        'other_params': ffmpeg_params,
        'input_0': ffmpeg_input_0,
        'input_1': ffmpeg_input_1,
        'input_2': ffmpeg_input_2,
    }

    # If we constantly run and monitor for drive added or not.
    if video_settings['run_type'] in ['MONITOR', 'MONITOR_ONCE']:
        got_drive = False
        print("Monitoring for TeslaCam Drive to be inserted. Press CTRL-C to"
              " stop")
        while True:
            try:
                source_folder, source_partition = get_tesladashcam_folder()
                if source_folder is None:
                    # Nothing found, sleep for 1 minute and check again.
                    if got_drive:
                        print("TeslaCam drive has been ejected.")
                        print("Monitoring for TeslaCam Drive to be inserted. "
                              "Press CTRL-C to stop")

                    sleep(MONITOR_SLEEP_TIME)
                    got_drive = False
                    continue

                # As long as TeslaCam drive is still attached we're going to
                # keep on waiting.
                if got_drive:
                    sleep(MONITOR_SLEEP_TIME)
                    continue

                # TeslaCam Folder found, returning it.
                print("TeslaCam folder found on {partition}.".format(
                    partition=source_partition
                ))
                if args.system_notification:
                    notify("TeslaCam", "Started",
                           "TeslaCam folder found on {partition}.".format(
                               partition=source_partition
                           ))
                # Got a folder, append what was provided as source unless
                # . was provided in which case everything is done.
                if video_settings['source_folder'][0] != '.':

                    source_folder = (os.path.join(
                        source_folder,
                        video_settings['source_folder'][0]))

                    folders = get_movie_files([source_folder],
                                              args.exclude_subdirs,
                                              video_settings)

                    if video_settings['run_type'] == 'MONITOR':
                        # We will continue to monitor hence we need to
                        # ensure we
                        # always have a unique final movie name.
                        movie_filename = video_settings['target_filename']
                        movie_filename = movie_filename + '_' if \
                            movie_filename is not None else ''
                        movie_filename = movie_filename + \
                                         datetime.today().strftime(
                                             '%Y-%m-%d_%H_%M')

                        video_settings.update({movie_filename: movie_filename})

                    process_folders(folders, video_settings, True,
                                    args.delete_source)

                if args.system_notification:
                    notify("TeslaCam", "Completed",
                           "Processing of movies has completed.".format(
                               partition=source_partition
                           ))
                # Stop if we're only to monitor once and then exit.
                if video_settings['run_type'] == 'MONITOR_ONCE':
                    print("Exiting monitoring as asked process once.")
                    break

                got_drive = True
                print("Waiting for TeslaCam Drive to be ejected. Press "
                      "CTRL-C to stop")
            except KeyboardInterrupt:
                print("Monitoring stopped due to CTRL-C.")
                break
    else:
        folders = get_movie_files(video_settings['source_folder'],
                                  args.exclude_subdirs,
                                  video_settings)
        process_folders(folders, video_settings, False, args.delete_source)


sys.exit(main())
