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

VERSION = {
    'major': 0,
    'minor': 1,
    'patch': 9,
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

MOVIE_LAYOUT = {
    # Layout:
    #  [Left_Clip][Front_Clip][Right_Clip]
    'WIDESCREEN': {
        'video_x': 1920,
        'video_y': 480,
        'clip_x': 640,  # 1/3 of video width
        'clip_y': 480,  # Same as video height
        'left_x': 0,  # Left of video
        'left_y': 0,  # Top of video
        'front_x': 640,  # Right of left clip
        'front_y': 0,  # Top of video
        'right_x': 1280,  # Right-most clip
        'right_y': 0,  # Top of video
        'left_options': '',
        'front_options': '',
        'right_options': '',
        'swap_left_rear': False,
    },
    # Layout:
    #       [Front_Clip]
    #  [Left_Clip][Right_Clip]
    'FULLSCREEN': {
        'video_x': 1280,
        'video_y': 960,
        'clip_x': 640,  # 1/3 of video width
        'clip_y': 480,  # Same as video height
        'left_x': 0,  # Left of video
        'left_y': 480,  # Bottom of video
        'front_x': 320,  # Middle of video
        'front_y': 0,  # Top of video
        'right_x': 640,  # Right of left clip
        'right_y': 480,  # Bottom of video
        'left_options': '',
        'front_options': '',
        'right_options': '',
        'swap_left_rear': False,
    },
    'PERSPECTIVE': {
        'video_x': 980,
        'video_y': 380,
        'clip_x': 320,  # 1/3 of video width
        'clip_y': 240,  # Same as video height
        'left_x': 5,  # Left of video
        'left_y': 5,  # Bottom of video
        'front_x': 330,  # Middle of video
        'front_y': 5,  # Top of video
        'right_x': 655,  # Right of left clip
        'right_y': 5,  # Bottom of video
        'left_options': ', pad=iw+4:11/6*ih:-1:30:0x00000000,'
                        'perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:'
                        'x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination',
        'front_options': '',
        'right_options': ', pad=iw+4:11/6*ih:-1:30:0x00000000,'
                         'perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:'
                         'x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination',
        'swap_left_rear': False,
    },
    'DIAGONAL': {
        'video_x': 980,
        'video_y': 380,
        'clip_x': 320,  # 1/3 of video width
        'clip_y': 240,  # Same as video height
        'left_x': 5,  # Left of video
        'left_y': 5,  # Bottom of video
        'front_x': 330,  # Middle of video
        'front_y': 5,  # Top of video
        'right_x': 655,  # Right of left clip
        'right_y': 5,  # Bottom of video
        'left_options': ', pad=iw+4:11/6*ih:-1:30:0x00000000,'
                        'perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:'
                        'x2=0:y2=6*H/5:x3=W:y3=410:sense=destination',
        'front_options': '',
        'right_options': ', pad=iw+4:11/6*ih:-1:30:0x00000000,'
                         'perspective=x0=0:y0=-3/44*H:x1=W:y1=1*H/5:'
                         'x2=0:y2=410:x3=W:y3=6*H/5:sense=destination',
        'swap_left_rear': False,
    },
}

MOVIE_QUALITY = {
    'HIGH': '18',
    'MEDIUM': '20',
    'LOW': '23',
    'LOWER': '28',
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
    'win32': 'C\:\\Windows\\Fonts\\arial.ttf',
    'cygwin': '/cygdrive/c/Windows/Fonts/arial.ttf',
    'linux': '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
}

HALIGN = {
    'LEFT': '10',
    'CENTER': '(w/2-text_w/2)',
    'RIGHT': '(w-text_w)',
}

VALIGN = {
    'TOP': '10',
    'MIDDLE': '(h/2-(text_h/2))',
    'BOTTOM': '(h-(text_h*2))',
}


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


def get_movie_files(source_folder, exclude_subdirs, ffmpeg):
    """ Find all the clip files within folder (and subfolder if requested) """
    # Retrieve all the video files in current path:
    search_path = os.path.join(source_folder, '*.mp4')
    files = (glob(search_path))

    if not exclude_subdirs:
        # Search through all sub folders as well.
        search_path = os.path.join(source_folder, '*', '*.mp4')
        files = files + (glob(search_path))

    folder_list = {}
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

        front_filename = str(filename_timestamp) + '-front.mp4'
        left_filename = str(filename_timestamp) + '-left_repeater.mp4'
        right_filename = str(filename_timestamp) + '-right_repeater.mp4'

        # Confirm we have at least a front, left, or rear movie file:
        if not os.path.isfile(
                os.path.join(
                    movie_folder, front_filename)) \
                and \
                not os.path.isfile(
                    os.path.join(
                        movie_folder,
                        left_filename)) and \
                not os.path.isfile(
                    os.path.join(
                        movie_folder, right_filename)):
            continue

        # Get meta data for each video to determine creation time and duration.
        metadata = get_metadata(ffmpeg, [
            os.path.join(movie_folder, front_filename),
            os.path.join(movie_folder, left_filename),
            os.path.join(movie_folder, right_filename),
        ])

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
                    if item['timestamp'] < video_timestamp else video_timestamp

        movie_info = {
            'movie_folder': movie_folder,
            'timestamp': video_timestamp,
            'duration': duration,
            'video_info': video_info,
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

    if video_settings['swap_left_right']:
        camera_2 = left_camera
        camera_0 = right_camera
    else:
        camera_0 = left_camera
        camera_2 = right_camera

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
            width=MOVIE_LAYOUT[movie_layout]['clip_x'],
            height=MOVIE_LAYOUT[movie_layout]['clip_y'],
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
            width=MOVIE_LAYOUT[movie_layout]['clip_x'],
            height=MOVIE_LAYOUT[movie_layout]['clip_y'],
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
            width=MOVIE_LAYOUT[movie_layout]['clip_x'],
            height=MOVIE_LAYOUT[movie_layout]['clip_y'],
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
        if movie_filename == clips_list[0]:
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
                shutil.move(clips_list[0], movie_filename)
            except OSError as exc:
                print("\t\tError trying to move file {} to {}: {}".format(
                    clips_list[0],
                    movie_filename,
                    exc))
                return None
        else:
            try:
                shutil.copyfile(clips_list[0], movie_filename)
            except OSError as exc:
                print("\t\tError trying to copy file {} to {}: {}".format(
                    clips_list[0],
                    movie_filename,
                    exc))
                return None

        return movie_filename

    # Go through the list of clips to create the command.
    ffmpeg_concat_input = []
    concat_filter_complex = ''
    total_clips = 0
    for filename in clips_list:
        if not os.path.isfile(filename):
            print("\t\tFile {} does not exist anymore, skipping.".format(
                filename
            ))
            continue

        ffmpeg_concat_input = ffmpeg_concat_input + ['-i', filename]
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

        movie_filename = os.path.split(folder_name)[1]
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
        delete_folder_files = delete_source
        delete_file_list = []

        for clip_number, filename_timestamp in enumerate(sorted(files)):
            video_timestamp_info = files[filename_timestamp]
            clip_name = create_intermediate_movie(
                filename_timestamp,
                video_timestamp_info,
                video_settings,
                clip_number,
                len(files)
            )

            if clip_name is not None:
                # Movie was created, store name for concatenation.
                folder_clips.append(clip_name)

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
        print("\t\tCreating movie {}, please be patient.".format(
            movie_filename))

        movie_name = create_movie(
            folder_clips,
            movie_filename,
            video_settings,
        )

        # Add this one to our list for final concatenation
        if movie_name is not None:
            dashcam_clips.append(movie_name)
            # Delete the intermediate files we created.
            if not video_settings['keep_intermediate']:
                delete_intermediate(folder_clips)

            # Delete the source files if stated to delete.
            if delete_folder_files:
                print("\t\tDeleting files and folder {folder_name}".format(
                    folder_name=folder_name
                ))
                delete_intermediate(delete_file_list)
                # And delete the folder.
                delete_intermediate([folder_name])

            print("\tMovie {base_name} for folder {folder_name} is "
                  "ready.".format(
                      base_name=movie_name,
                      folder_name=folder_name,
                  ))

    # Now that we have gone through all the folders merge.
    # We only do this if merge is enabled OR if we only have 1 clip.
    # Reason to also do it with 1 is to put the name correctly for the
    # movie
    # especially if a filename was given.
    movie_name = None
    if video_settings['merge_subdirs'] or len(folders) == 1:
        print("\tCreating movie {}, please be patient.".format(
            video_settings['movie_filename']))

        movie_name = create_movie(
            dashcam_clips,
            video_settings['movie_filename'],
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
    base_path = getattr(sys, '_MEIPASS', Path(__file__).parent)
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

    parser = argparse.ArgumentParser(
        description='tesla_dashcam - Tesla DashCam & Sentry Video Creator',
        epilog=epilog,
        formatter_class=SmartFormatter)

    parser.add_argument('--version',
                        action='version',
                        version=' %(prog)s ' + VERSION_STR
                        )
    parser.add_argument('source',
                        type=str,
                        help="Folder containing the saved camera files.")

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
                        type=str,
                        help="R|Path/Filename for the new movie file. "
                             "Intermediate files will be stored in same "
                             "folder.\n"
                             "If not provided then resulting movie files "
                             "will be created within same folder as source "
                             "files."
                        )

    parser.add_argument('--keep-intermediate',
                        dest='keep_intermediate',
                        action='store_true',
                        help='Do not remove the intermediate video files that '
                             'are created')

    parser.add_argument('--no-notification',
                        dest='system_notification',
                        action='store_false',
                        help='Do not create a notification upon '
                             'completion.')

    parser.add_argument('--layout',
                        required=False,
                        choices=['WIDESCREEN',
                                 'FULLSCREEN',
                                 'DIAGONAL',
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
                                 default=16,
                                 help="Font size for timestamp.")

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

    monitor_group.add_argument('--delete_source',
                               dest='delete_source',
                               action='store_true',
                               help='Delete the processed files on the '
                                    'TeslaCam drive.'
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
                                    beta_version == -1:
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

    ffmpeg_base = black_base + black_size.format(
        width=MOVIE_LAYOUT[args.layout]['video_x'],
        height=MOVIE_LAYOUT[args.layout]['video_y'],
    ) + '[base];'

    ffmpeg_black_video = black_base + black_size

    ffmpeg_input_0 = 'setpts=PTS-STARTPTS, ' \
                     'scale={clip_width}x{clip_height} {mirror}{options}' \
                     ' [left];'.format(
                         clip_width=MOVIE_LAYOUT[args.layout]['clip_x'],
                         clip_height=MOVIE_LAYOUT[args.layout]['clip_y'],
                         mirror=mirror_sides,
                         options=MOVIE_LAYOUT[args.layout]['left_options'],
                     )

    ffmpeg_input_1 = 'setpts=PTS-STARTPTS, ' \
                     'scale={clip_width}x{clip_height} {options}' \
                     ' [front];'.format(
                         clip_width=MOVIE_LAYOUT[args.layout]['clip_x'],
                         clip_height=MOVIE_LAYOUT[args.layout]['clip_y'],
                         options=MOVIE_LAYOUT[args.layout]['front_options'],
                     )

    ffmpeg_input_2 = 'setpts=PTS-STARTPTS, ' \
                     'scale={clip_width}x{clip_height} {mirror}{options}' \
                     ' [right];'.format(
                         clip_width=MOVIE_LAYOUT[args.layout]['clip_x'],
                         clip_height=MOVIE_LAYOUT[args.layout]['clip_y'],
                         mirror=mirror_sides,
                         options=MOVIE_LAYOUT[args.layout]['right_options'],
                     )

    ffmpeg_video_position = \
        '[base][left] overlay=eof_action=pass:repeatlast=0:' \
        'x={left_x}:y={left_y} [left1];' \
        '[left1][front] overlay=eof_action=pass:repeatlast=0:' \
        'x={front_x}:y={front_y} [front1];' \
        '[front1][right] overlay=eof_action=pass:repeatlast=0:' \
        'x={right_x}:y={right_y}'.format(
            left_x=MOVIE_LAYOUT[args.layout]['left_x'],
            left_y=MOVIE_LAYOUT[args.layout]['left_y'],
            front_x=MOVIE_LAYOUT[args.layout]['front_x'],
            front_y=MOVIE_LAYOUT[args.layout]['front_y'],
            right_x=MOVIE_LAYOUT[args.layout]['right_x'],
            right_y=MOVIE_LAYOUT[args.layout]['right_y'],
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

        ffmpeg_timestamp = ffmpeg_timestamp + \
            'fontcolor={fontcolor}:fontsize={fontsize}:' \
            'borderw=2:bordercolor=black@1.0:' \
            'x={halign}:y={valign}:'.format(
                fontcolor=args.fontcolor,
                fontsize=args.fontsize,
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
            encoding = encoding + '_mac' if sys.platform == 'darwin' else \
                encoding + '_nvidia'

            video_encoding = video_encoding + \
                ['-b:v',
                 '2500K'
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

    # Determine the target folder.
    target_folder = args.source if args.output is None else args.output
    if not os.path.isdir(target_folder):
        target_folder = os.path.split(str(args.output))[0]

    # Determine final movie name.
    movie_filename = args.output
    if movie_filename is None or os.path.isdir(str(movie_filename)):
        if movie_filename is None:
            movie_filename = args.source

        # Get the actual folder name as we're using that to create the movie
        # name
        folder, filename = os.path.split(movie_filename)

        # If there was a trailing seperator provided then it will be empty,
        # redo split then.
        if filename == '':
            filename = os.path.split(folder)[1]

        # Now add full path to it.
        movie_filename = os.path.join(movie_filename, filename)
    else:
        # Got complete with filename.
        movie_filename = args.output

    # Make sure it ends in .mp4
    if os.path.splitext(movie_filename)[1] != '.mp4':
        movie_filename = movie_filename + '.mp4'

    # Determine if left and right cameras should be swapped or not.
    if args.swap is None:
        # Default is set based on layout chosen.
        if args.layout == 'FULLSCREEN':
            # FULLSCREEN is different, if doing mirror then default should
            # not be swapping. If not doing mirror then default should be
            # to swap making it seem more like a "rear" camera.
            swap_left_right = not side_camera_as_mirror
        else:
            swap_left_right = MOVIE_LAYOUT[args.layout]['swap_left_rear']
    else:
        swap_left_right = args.swap

    video_settings = {
        'target_folder': target_folder,
        'merge_subdirs': args.merge_subdirs,
        'movie_filename': movie_filename,
        'keep_intermediate': args.keep_intermediate,
        'notification': args.system_notification,
        'swap_left_right': swap_left_right,
        'movie_layout': args.layout,
        'movie_speed': speed,
        'video_encoding': video_encoding,
        'movie_encoding': args.encoding,
        'movie_compression': args.compression,
        'movie_quality': args.quality,
        'background': ffmpeg_black_video,
        'ffmpeg_exec': ffmpeg,
        'base': ffmpeg_base,
        'clip_positions': ffmpeg_video_position,
        'timestamp_text': ffmpeg_timestamp,
        'ffmpeg_speed': ffmpeg_speed,
        'other_params': ffmpeg_params,
        'input_0': ffmpeg_input_0,
        'input_1': ffmpeg_input_1,
        'input_2': ffmpeg_input_2,
    }

    # If we constantly run and monitor for drive added or not.
    if args.monitor or args.monitor_once:
        movie_filename, _ = os.path.splitext(video_settings['movie_filename'])
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
                if args.source != '.':
                    source_folder = os.path.join(source_folder, args.source)

                    folders = get_movie_files(source_folder,
                                              args.exclude_subdirs,
                                              ffmpeg)

                    if not args.monitor_once:
                        # We will continue to monitor hence we need to
                        # ensure we
                        # always have a unique final movie name.
                        mv_filename = movie_filename + '_' + \
                            datetime.today().strftime(
                                '%Y-%m-%d_%H_%M')

                        video_settings.update({movie_filename: mv_filename})

                    process_folders(folders, video_settings, True,
                                    args.delete_source)

                if args.system_notification:
                    notify("TeslaCam", "Completed",
                           "Processing of movies has completed.".format(
                               partition=source_partition
                           ))
                # Stop if we're only to monitor once and then exit.
                if args.monitor_once:
                    print("Exiting monitoring as asked process once.")
                    break

                got_drive = True
                print("Waiting for TeslaCam Drive to be ejected. Press "
                      "CTRL-C to stop")
            except KeyboardInterrupt:
                print("Monitoring stopped due to CTRL-C.")
                break
    else:
        folders = get_movie_files(args.source, args.exclude_subdirs, ffmpeg)
        process_folders(folders, video_settings, False, False)


sys.exit(main())
