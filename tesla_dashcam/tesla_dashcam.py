
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
        'left_options':  '',
        'front_options': '',
        'right_options': '',
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
        'right_y': 480,  # Bottom of video
        'left_options': '',
        'front_options': '',
        'right_options': '',
    },
    'PERSPECTIVE': {
        'video_x': 980,
        'video_y': 380,
        'clip_x':  320,  # 1/3 of video width
        'clip_y':  240,  # Same as video height
        'left_x':  5,  # Left of video
        'left_y':  5,  # Bottom of video
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
    'win32': 'C\:\\Windows\\Fonts\\arial.ttf',
    'cygwin': 'C\:\\Windows\\Fonts\\arial.ttf',
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

class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)

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
        formatter_class=SmartFormatter)
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('source',
                        type=str,
                        help='Folder containing the saved camera files')

    parser.add_argument('--output',
                        required=False,
                        type=str,
                        help='Path/Filename for the new movie file.')

    parser.add_argument('--layout',
                        required=False,
                        choices=['WIDESCREEN',
                                 'FULLSCREEN',
                                 'PERSPECTIVE', ],
                        default='PERSPECTIVE',
                        help='R|Layout of the created video.\n'
                             '    PERSPECTIVE: Front camera center top, '
                             'side cameras next to it in perspective.\n'
                             '    WIDESCREEN: Output from all 3 cameras are '
                             'next to each other.\n'
                             '    FULLSCREEN: Front camera center top, '
                             'side cameras underneath it.')

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
                        help='Encoding to use. x264 can be viewed on more '
                             'devices but results in bigger file. x265 is '
                             'newer encoding standard but not all devices '
                             'support this yet.')

    parser.add_argument('--timestamp',
                        dest='timestamp',
                        action='store_true',
                        help='Include timestamp in video')
    parser.add_argument('--no-timestamp',
                        dest='timestamp',
                        action='store_false',
                        help='Do not include timestamp in video')
    parser.set_defaults(timestamp=True)

    parser.add_argument('--halign',
                        required=False,
                        choices=['LEFT',
                                 'CENTER',
                                 'RIGHT', ],
                        default='CENTER',
                        help='Horizontal alignment for timestamp')

    parser.add_argument('--valign',
                        required=False,
                        choices=['TOP',
                                 'MIDDLE',
                                 'BOTTOM', ],
                        default='BOTTOM',
                        help='Vertical Alignment for timestamp')

    parser.add_argument('--font',
                        required=False,
                        type=str,
                        default=DEFAULT_FONT.get(sys.platform, None),
                        help='Fully qualified filename (.ttf) to the '
                             'font to be chosen for timestamp.')

    parser.add_argument('--fontsize',
                        required=False,
                        type=int,
                        default=16,
                        help='Font size for timestamp.')

    parser.add_argument('--fontcolor',
                        required=False,
                        type=str,
                        default='white',
                        help='R|Font color for timestamp. Any color is '
                             'accepted as a color string or RGB value.\n'
                             'Some potential values are:\n'
                             '    white\n'
                             '    yellowgreen\n'
                             '    yellowgreen@0.9\n'
                             '    Red\n'
                             '    0x2E8B57\n'
                             'For more information on this see ffmpeg '
                             'documentation for color: '
                             'https://ffmpeg.org/ffmpeg-utils.html#Color'
)

    parser.add_argument('--ffmpeg',
                        required=False,
                        type=str,
                        default=FFMPEG,
                        help='Path and filename for ffmpeg. Specify if '
                             'ffmpeg is not within path.')



    args = parser.parse_args()

    ffmpeg = args.ffmpeg

    base_filter = 'color=duration={duration}:'

    ffmpeg_filter = \
        's={width}x{height}:c=black [base];' \
        '[0:v] setpts=PTS-STARTPTS, scale={clip_width}x{clip_height} ' \
        '{left_options} [left];'\
        '[1:v] setpts=PTS-STARTPTS, scale={clip_width}x{clip_height} ' \
        '{front_options} [front];'\
        '[2:v] setpts=PTS-STARTPTS, scale={clip_width}x{clip_height} ' \
        '{right_options} [right];'\
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
            left_options=MOVIE_LAYOUT[args.layout]['left_options'],
            front_options=MOVIE_LAYOUT[args.layout]['front_options'],
            right_options=MOVIE_LAYOUT[args.layout]['right_options'],
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
            'fontcolor={fontcolor}:fontsize={fontsize}:'\
            'borderw=2:bordercolor=black@1.0:'\
            'x={halign}:y={valign}:'.format(
                fontcolor=args.fontcolor,
                fontsize=args.fontsize,
                valign=VALIGN[args.valign],
                halign=HALIGN[args.halign],
            )

        ffmpeg_timestamp = ffmpeg_timestamp + \
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
            ffmpeg,
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
    if args.output is None:
        # Get the actual folder name as we're using that to create the movie
        # name
        folder, movie_filename = os.path.split(args.source)
        # If there was a trailing seperator provided then it will be empty,
        # redo split then.
        if movie_filename == '':
            movie_filename = os.path.split(folder)[1]

        # Now add full path to it.
        movie_filename = os.path.join(args.source, movie_filename)
    else:
        movie_filename = args.output

    # Make sure it ends in .mp4
    if os.path.splitext(movie_filename)[1] != 'mp4':
        movie_filename = movie_filename + '.mp4'

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

    ffmpeg_command = [ffmpeg] + \
        ffmpeg_concat_input + \
        ffmpeg_params + \
        ['-y', movie_filename]

    # Creating movie
    print("Creating movie {}, please be patient.".format(movie_filename))

    try:
        run(ffmpeg_command, capture_output=True, check=True)
    except CalledProcessError as exc:
        print("Error trying to create movie {base_name}. RC: {rc}\n"
              "Command: {command}\n"
              "Error: {stderr}\n\n".format(
                base_name=movie_filename,
                rc=exc.returncode,
                command=exc.cmd,
                stderr=exc.stderr,
                ))
    else:
        print("Movie {base_name} has been created, enjoy.".format(
            base_name=movie_filename))


sys.exit(main())
