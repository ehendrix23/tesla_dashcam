
import argparse
import os
import sys
from datetime import datetime
from glob import glob
from re import search
from subprocess import CalledProcessError, run

from tzlocal import get_localzone

FFMPEG = 'ffmpeg'
MOVIE_LAYOUT = {
    # Layout:
    #  [Left_Clip][Front_Clip][Right_Clip]
    'WIDESCREEN': {
        'video_x': 1920,
        'video_y': 480,
        'clip_x': 640,    # 1/3 of video width
        'clip_y': 480,    # Same as video height
        'left_x': 0,      # Left of video
        'left_y': 0,      # Top of video
        'front_x': 640,   # Right of left clip
        'front_y': 0,     # Top of video
        'right_x': 1280,  # Right-most clip
        'right_y': 0,     # Top of video
    },
    # Layout:
    #       [Front_Clip]
    #  [Left_Clip][Right_Clip]
    'FULLSCREEN': {
        'video_x': 1280,
        'video_y': 960,
        'clip_x':  640,  # 1/3 of video width
        'clip_y':  480,  # Same as video height
        'left_x':  0,    # Left of video
        'left_y':  480,  # Bottom of video
        'front_x': 320,  # Middle of video
        'front_y': 0,    # Top of video
        'right_x': 640,  # Right of left clip
        'right_y': 320,  # Bottom of video
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
    'x265': 'libx265',
}

DEFAULT_FONT = {
    'darwin': '/Library/Fonts/Arial.ttf',
    'windows': 'C\:\\Windows\\Fonts\\arial.ttf',
}


def get_metadata(ffmpeg, filenames):
    # Get meta data for each video to determine creation time and duration.
    ffmpeg_command = [
        ffmpeg,
    ]

    for file in filenames:
        ffmpeg_command.append('-i')
        ffmpeg_command.append(file)

    ffmpeg_command.append('-hide_banner')

    command_result = run(ffmpeg_command, capture_output=True, text=True)

    input_counter = 0
    file = ''
    metadata = []
    wait_for_input_line = True
    for line in command_result.stderr.splitlines():
        if search("^Input #", line) is not None:
            file = filenames[input_counter]
            input_counter += 1
            timestamp = None
            wait_for_input_line = False
            continue

        if wait_for_input_line:
                continue

        if search("^ *creation_time ", line) is not None:
            line_split = line.split(':', 1)
            timestamp = datetime.strptime(line_split[1].strip(),
                                          "%Y-%m-%dT%H:%M:%S.%f%z")
            continue

        if search("^ *Duration: ", line) is not None:
            line_split = line.split(',')
            line_split = line_split[0].split(':', 1)
            duration_list = line_split[1].split(':')
            duration = int(duration_list[0])*60*60 + \
                int(duration_list[1])*60 + \
                int(duration_list[2].split('.')[0]) + \
                (float(duration_list[2].split('.')[1]) / 100)

            metadata.append(
                {
                    'filename':  file,
                    'timestamp': timestamp,
                    'duration':  duration,
                }
            )
            continue

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(
        description='tesla_dashcam - Tesla DashCam Creator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--source',
                        required=True,
                        type=str,
                        help='Folder containing the saved camera files')

    parser.add_argument('--output',
                        required=True,
                        type=str,
                        help='Path/Filename for the new movie file.')

    parser.add_argument('--layout',
                        required=False,
                        choices=['WIDESCREEN',
                                 'FULLSCREEN', ],
                        default='WIDESCREEN',
                        help='Layout of the video. Widescreen puts video of '
                             'all 3 cameras next to each other. Fullscreen '
                             'puts the front camera on top in middle and '
                             'side cameras below it next to each other')

    parser.add_argument('--quality',
                        required=False,
                        choices=['LOWEST',
                                 'LOWER',
                                 'LOW',
                                 'MEDIUM',
                                 'HIGH'],
                        default='LOWER',
                        help='Define the quality setting for the video, '
                             'higher quality means bigger file size but '
                             'might not be noticeable.')

    parser.add_argument('--compression',
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
                        help='Speed to optimize video. Faster speed '
                             'results in a bigger file. This does not impact '
                             'the quality of the video, just how much time '
                             'is used to compress it.')

    parser.add_argument('--encoding',
                        required=False,
                        choices=['x264',
                                 'x265'],
                        default='x264',
                        help='Encoding to use. x264 is can be viewed on more '
                             'devices but results in bigger file. x265 is '
                             'newer encoding standard')

    parser.add_argument('--timestamp',
                        dest='timestamp',
                        action='store_true',
                        help='Include timestamp in video')
    parser.add_argument('--no-timestamp',
                        dest='timestamp',
                        action='store_false',
                        help='Do not include timestamp in video')
    parser.set_defaults(timestamp=True)

    parser.add_argument('--ffmpeg',
                        required=False,
                        type=str,
                        default=FFMPEG,
                        help='Path and filename for ffmpeg. Specify if '
                             'ffmpeg is not within path.')

    parser.add_argument('--font',
                        required=False,
                        type=str,
                        default=DEFAULT_FONT.get(sys.platform, None),
                        help='Fully qualified filename (.ttf) to the '
                             'font to be chosen for timestamp.')

    args = parser.parse_args()

    ffmpeg = args.ffmpeg

    base_filter = 'color=duration={duration}:'

    ffmpeg_filter = \
        's={width}x{height}:c=black [base];' \
        '[0:v] setpts=PTS-STARTPTS, scale={clip_width}x{clip_height} [left];'\
        '[1:v] setpts=PTS-STARTPTS, scale={clip_width}x{clip_height} [front];'\
        '[2:v] setpts=PTS-STARTPTS, scale={clip_width}x{clip_height} [right];'\
        '[base][left] overlay=eof_action=pass:repeatlast=0:' \
        'x={left_x}:y={left_y} [left1];' \
        '[left1][front] overlay=eof_action=pass:repeatlast=0:' \
        'x={front_x}:y={front_y} [front1];' \
        '[front1][right] overlay=eof_action=pass:repeatlast=0:' \
        'x={right_x}:y={right_y}'.format(
            width=MOVIE_LAYOUT[args.layout]['video_x'],
            height=MOVIE_LAYOUT[args.layout]['video_y'],
            clip_width=MOVIE_LAYOUT[args.layout]['clip_x'],
            clip_height=MOVIE_LAYOUT[args.layout]['clip_y'],
            left_x=MOVIE_LAYOUT[args.layout]['left_x'],
            left_y=MOVIE_LAYOUT[args.layout]['left_y'],
            front_x=MOVIE_LAYOUT[args.layout]['front_x'],
            front_y=MOVIE_LAYOUT[args.layout]['front_y'],
            right_x=MOVIE_LAYOUT[args.layout]['right_x'],
            right_y=MOVIE_LAYOUT[args.layout]['right_y'],
        )

    if args.timestamp:
        if args.font is not None and args.font != '':
            font_file = args.font
        else:
            font_file = DEFAULT_FONT.get(sys.platform, None)

        if font_file is None:
            print("Unable to get a font file. Please provide valid font file.")
            return

        ffmpeg_timestamp = ' [tmp3]; [tmp3] drawtext=' \
                           'fontfile={fontfile}:'.format(fontfile=font_file)

        ffmpeg_timestamp = ffmpeg_timestamp + \
            'fontcolor=white:fontsize=24:'\
            'box=1:boxcolor=black@0.4:'\
            'x=(w/2-text_w/2):y=(h-(text_h*2)):'\
            "text='%{{pts\:localtime\:{epoch_time}\:%x %X}}'"

        ffmpeg_filter = ffmpeg_filter + ffmpeg_timestamp

    ffmpeg_params = ['-c:v',
                     MOVIE_ENCODING[args.encoding],
                     '-preset',
                     args.compression,
                     '-crf',
                     MOVIE_QUALITY[args.quality]
                     ]

    dashcam_clips = []
    concat_filter_complex = ''
    ffmpeg_concat_input = []

    search_path = os.path.join(args.source, '*-front.mp4')
    files = (glob(search_path))
    for clip_number, file in enumerate(sorted(files)):
        # We first stack (combine the 3 different camera video files into 1
        # and then we concatenate.
        base_name = file.rsplit('-', 1)
        base_name = base_name[0]
        left_camera = base_name + '-left_repeater.mp4'
        front_camera = base_name + '-front.mp4'
        right_camera = base_name + '-right_repeater.mp4'
        temp_movie_name = base_name + '.mp4'

        # Get meta data for each video to determine creation time and duration.
        metadata = get_metadata(ffmpeg, [left_camera, front_camera,
                                         right_camera])

        # Get the longest duration:
        duration = 0
        timestamp = None
        for item in metadata:
            duration = item['duration'] if item['duration'] > duration else \
                duration

            if timestamp is None:
                timestamp = item['timestamp']
            else:
                timestamp = item['timestamp'] if item['timestamp'] < \
                                                 timestamp else timestamp

        # If we could get a timestamp then retrieve it from the filename
        # instead
        if timestamp is None:
            # Get the pure filename which would be timestamp in format:
            # YYYY-MM-DD_HH_MM
            base_filename = base_name.rsplit(os.sep, 1)
            # Split in date and time parts
            timestamps = base_filename[1].split('_')
            # Split date
            date = timestamps[0].split('-')
            # Split time
            time = timestamps[1].split('-')

            timestamp = datetime(int(date[0]),
                                 int(date[1]),
                                 int(date[2]),
                                 int(time[0]),
                                 int(time[1]))

        local_timestamp = timestamp.astimezone(get_localzone())
        print("Processing clip {clip_number}/{total_clips} from {timestamp} "
              "and {duration} seconds long.".format(
                clip_number=clip_number+1,
                total_clips=len(files),
                timestamp=local_timestamp.strftime("%x %X"),
                duration=int(duration),
                ))

        epoch_timestamp = int(timestamp.timestamp())

        temp_ffmpeg_filter = \
            base_filter.format(duration=duration) + \
            ffmpeg_filter.format(epoch_time=epoch_timestamp)
        ffmpeg_command = [
            FFMPEG,
            '-i',
            left_camera,
            '-i',
            front_camera,
            '-i',
            right_camera,
            '-filter_complex',
            temp_ffmpeg_filter
        ] + ffmpeg_params

        ffmpeg_command = ffmpeg_command + ['-y', temp_movie_name]

        # Run the command.
        try:
            # print(ffmpeg_command)
            run(ffmpeg_command, capture_output=True, check=True)
        except CalledProcessError as exc:
            print("Error trying to create clip for {base_name}. RC: {rc}\n"
                  "Command: {command}\n"
                  "Error: {stderr}\n\n".format(
                    base_name=base_name,
                    rc=exc.returncode,
                    command=exc.cmd,
                    stderr=exc.stderr,
                    )
                  )
        else:
            ffmpeg_concat_input = ffmpeg_concat_input + ['-i', temp_movie_name]

            concat_filter_complex = concat_filter_complex + \
                '[{clip}:v:0] '.format(
                                        clip=len(dashcam_clips)
                                    )

            dashcam_clips.append(temp_movie_name)

    # Now that all individuals clips are done, concatanate them all together.
    concat_filter_complex = concat_filter_complex + \
        "concat=n={total_clips}:v=1:a=0 [v]".format(
            total_clips=len(dashcam_clips),
        )
    ffmpeg_params = ['-filter_complex',
                     concat_filter_complex,
                     '-map',
                     '[v]',
                     '-c:v',
                     MOVIE_ENCODING[args.encoding],
                     '-preset',
                     args.compression,
                     '-crf',
                     MOVIE_QUALITY[args.quality]
                     ]

    ffmpeg_command = [FFMPEG] + \
        ffmpeg_concat_input + \
        ffmpeg_params + \
        ['-y', args.output]

    # Creating movie
    print("Creating movie {}, please be patient.".format(args.output))

    try:
        run(ffmpeg_command, capture_output=True, check=True)
    except CalledProcessError as exc:
        print("Error trying to create movie {base_name}. RC: {rc}\n"
              "Command: {command}\n"
              "Error: {stderr}\n\n".format(
                base_name=args.output,
                rc=exc.returncode,
                command=exc.cmd,
                stderr=exc.stderr,
                ))
    else:
        print("Movie {base_name} has been created, enjoy.".format(
            base_name=args.output))


if __name__ == '__main__':
    sys.exit(main())
