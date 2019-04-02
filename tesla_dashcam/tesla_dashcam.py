import argparse
import os
import shutil
import sys
from datetime import datetime
from glob import glob
from pathlib import Path
from re import search
from subprocess import CalledProcessError, run

from tzlocal import get_localzone

VERSION='0.1.8'

FFMPEG = {
    'darwin': 'ffmpeg',
    'win32':  'ffmpeg.exe',
    'cygwin': 'ffmpeg',
    'linux':  'ffmpeg',
}

MOVIE_LAYOUT = {
    # Layout:
    #  [Left_Clip][Front_Clip][Right_Clip]
    'WIDESCREEN':  {
        'video_x':       1920,
        'video_y':       480,
        'clip_x':        640,  # 1/3 of video width
        'clip_y':        480,  # Same as video height
        'left_x':        0,  # Left of video
        'left_y':        0,  # Top of video
        'front_x':       640,  # Right of left clip
        'front_y':       0,  # Top of video
        'right_x':       1280,  # Right-most clip
        'right_y':       0,  # Top of video
        'left_options':  '',
        'front_options': '',
        'right_options': '',
        'swap_left_rear': False,
    },
    # Layout:
    #       [Front_Clip]
    #  [Left_Clip][Right_Clip]
    'FULLSCREEN':  {
        'video_x':       1280,
        'video_y':       960,
        'clip_x':        640,  # 1/3 of video width
        'clip_y':        480,  # Same as video height
        'left_x':        0,  # Left of video
        'left_y':        480,  # Bottom of video
        'front_x':       320,  # Middle of video
        'front_y':       0,  # Top of video
        'right_x':       640,  # Right of left clip
        'right_y':       480,  # Bottom of video
        'left_options':  '',
        'front_options': '',
        'right_options': '',
        'swap_left_rear': False,
    },
    'PERSPECTIVE': {
        'video_x':       980,
        'video_y':       380,
        'clip_x':        320,  # 1/3 of video width
        'clip_y':        240,  # Same as video height
        'left_x':        5,  # Left of video
        'left_y':        5,  # Bottom of video
        'front_x':       330,  # Middle of video
        'front_y':       5,  # Top of video
        'right_x':       655,  # Right of left clip
        'right_y':       5,  # Bottom of video
        'left_options':  ', pad=iw+4:11/6*ih:-1:30:0x00000000,'
                         'perspective=x0=0:y0=1*H/5:x1=W:y1=-3/44*H:'
                         'x2=0:y2=6*H/5:x3=7/8*W:y3=5*H/6:sense=destination',
        'front_options': '',
        'right_options': ', pad=iw+4:11/6*ih:-1:30:0x00000000,'
                         'perspective=x0=0:y1=1*H/5:x1=W:y0=-3/44*H:'
                         'x2=1/8*W:y3=6*H/5:x3=W:y2=5*H/6:sense=destination',
        'swap_left_rear': False,
    },
    'DIAGONAL':    {
        'video_x':       980,
        'video_y':       380,
        'clip_x':        320,  # 1/3 of video width
        'clip_y':        240,  # Same as video height
        'left_x':        5,  # Left of video
        'left_y':        5,  # Bottom of video
        'front_x':       330,  # Middle of video
        'front_y':       5,  # Top of video
        'right_x':       655,  # Right of left clip
        'right_y':       5,  # Bottom of video
        'left_options':  ', pad=iw+4:11/6*ih:-1:30:0x00000000,'
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
    'x265_mac':   'hevc_videotoolbox',
    'x265_intel': 'h265_qsv',
}

DEFAULT_FONT = {
    'darwin': '/Library/Fonts/Arial.ttf',
    'win32':  'C\:\\Windows\\Fonts\\arial.ttf',
    'cygwin': '/cygdrive/c/Windows/Fonts/arial.ttf',
    'linux':  '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
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


class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


    def _get_help_string(self, action):
        return argparse.ArgumentDefaultsHelpFormatter._get_help_string(self,
                                                                       action)


def get_metadata(ffmpeg, filenames):
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
            duration = int(duration_list[0]) * 60 * 60 + \
                       int(duration_list[1]) * 60 + \
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

    # If compiled then getting path of executable is different.
    if getattr(sys, 'frozen', False):
        ffmpeg_path = os.path.dirname(sys.executable)
    else:
        ffmpeg_path = Path(__file__).parent

    ffmpeg_default = os.path.join(ffmpeg_path, FFMPEG.get(sys.platform,
                                                          'ffmpeg'))

    # Check if ffmpeg exist, if not then hope it is in default path or
    # provided.
    if not os.path.isfile(ffmpeg_default):
        ffmpeg_default = FFMPEG.get(sys.platform, 'ffmpeg')

    parser = argparse.ArgumentParser(
        description='tesla_dashcam - Tesla DashCam & Senty Video Creator',
        epilog='This program requires ffmpeg which can be downloaded from: '
               'https://ffmpeg.org/download.html',
        formatter_class=SmartFormatter)
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--version', action='version', version=' %(prog)s '
                                                               + VERSION)
    parser.add_argument('source',
                        type=str,
                        help="Folder containing the saved camera files.")

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
                                     "For more information on this see ffmpeg "
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
                                    "impact the quality of the video, just how "
                                    "much time is used to compress it."
                               )

    parser.add_argument('--ffmpeg',
                        required=False,
                        type=str,
                        default=ffmpeg_default,
                        help='Path and filename for ffmpeg. Specify if '
                             'ffmpeg is not within path.')

    args = parser.parse_args()

    ffmpeg = args.ffmpeg

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
        mirror=mirror_sides,
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
                               filter_counter=filter_counter,
                               fontfile=font_file
                           )
        filter_counter+=1

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
    speed = 1/args.speed_up if args.speed_up  is not None else speed
    ffmpeg_speed = ''
    if speed != '':
        ffmpeg_speed =  filter_label.format(
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
        use_gpu = False if args.gpu else True

    if args.enc is None:
        encoding = args.encoding
        # GPU acceleration enabled
        if use_gpu:
            print("GPU acceleration enabled")
            encoding = encoding + '_mac' if sys.platform == 'darwin' else \
                encoding + '_nvenc'

            ffmpeg_params = ffmpeg_params + \
                            ['-b:v',
                             '2500K']

        ffmpeg_params = ffmpeg_params + \
                        ['-c:v',
                         MOVIE_ENCODING[encoding]
                        ]
    else:
        ffmpeg_params = ffmpeg_params + \
                        ['-c:v',
                         args.enc
                        ]

    dashcam_clips = []
    concat_filter_complex = ''
    ffmpeg_concat_input = []

    # Determine the target folder.
    target_folder = args.source if args.output is None else \
        os.path.split(args.output)[0]

    # Determine if left and right cameras should be swapped or not.
    if args.swap is None:
        # Default is set based on layout chosen.
        if args.layout == 'FULLSCREEN':
            # FULLSCREEN is different, if doing mirror then default should
            # not be swapping. If not doing mirror then default should be
            # to swap making it seem more like a "rear" camera.
            swap_left_rear = False if side_camera_as_mirror else True
        else:
            swap_left_rear = MOVIE_LAYOUT[args.layout]['swap_left_rear']
    else:
        swap_left_rear = args.swap

    search_path = os.path.join(args.source, '*-front.mp4')
    files = (glob(search_path))
    for clip_number, file in enumerate(sorted(files)):
        # We first stack (combine the 3 different camera video files into 1
        # and then we concatenate.
        base_name = file.rsplit('-', 1)
        base_name = base_name[0]

        camera_1 = base_name + '-front.mp4'
        if swap_left_rear:
            camera_2 = base_name + '-left_repeater.mp4'
            camera_0 = base_name + '-right_repeater.mp4'
        else:
            camera_0 = base_name + '-left_repeater.mp4'
            camera_2 = base_name + '-right_repeater.mp4'

        # Currently basename still has full path, get just the filename so
        # that we can provide the correct folder.
        _, temp_movie_name = os.path.split(base_name)
        temp_movie_name = os.path.join(target_folder, temp_movie_name) + '.mp4'

        # Get meta data for each video to determine creation time and duration.
        metadata = get_metadata(ffmpeg, [camera_0, camera_1, camera_2])

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

        # Confirm if files exist, if not replace with nullsrc
        input_count = 0
        if os.path.isfile(camera_0):
            ffmpeg_command_0 = [
                '-i',
                camera_0
            ]
            ffmpeg_camera_0 = '[0:v] ' + ffmpeg_input_0
            input_count += 1
        else:
            ffmpeg_command_0 = []
            ffmpeg_camera_0 = ffmpeg_black_video.format(
                duration=duration,
                speed=speed,
                width=MOVIE_LAYOUT[args.layout]['clip_x'],
                height=MOVIE_LAYOUT[args.layout]['clip_y'],
            ) + '[left];'

        if os.path.isfile(camera_1):
            ffmpeg_command_1 = [
                '-i',
                camera_1
            ]
            ffmpeg_camera_1 = '[' + str(input_count) + ':v] ' + ffmpeg_input_1
            input_count += 1
        else:
            ffmpeg_command_1 = []
            ffmpeg_camera_1 = ffmpeg_black_video.format(
                duration=duration,
                speed=speed,
                width=MOVIE_LAYOUT[args.layout]['clip_x'],
                height=MOVIE_LAYOUT[args.layout]['clip_y'],
            ) + '[front];'

        if os.path.isfile(camera_2):
            ffmpeg_command_2 = [
                '-i',
                camera_2
            ]
            ffmpeg_camera_2 = '[' + str(input_count) + ':v] ' + ffmpeg_input_2
            input_count += 1
        else:
            ffmpeg_command_2 = []
            ffmpeg_camera_2 = ffmpeg_black_video.format(
                duration=duration,
                speed=speed,
                width=MOVIE_LAYOUT[args.layout]['clip_x'],
                height=MOVIE_LAYOUT[args.layout]['clip_y'],
            ) + '[right];'

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
            clip_number=clip_number + 1,
            total_clips=len(files),
            timestamp=local_timestamp.strftime("%x %X"),
            duration=int(duration),
        ))

        epoch_timestamp = int(timestamp.timestamp())

        ffmpeg_filter = \
            ffmpeg_base.format(
                duration=duration,
                speed=speed,) + \
            ffmpeg_camera_0 + \
            ffmpeg_camera_1 + \
            ffmpeg_camera_2 + \
            ffmpeg_video_position + \
            ffmpeg_timestamp.format(epoch_time=epoch_timestamp) + \
            ffmpeg_speed

        ffmpeg_command = [ ffmpeg ] + \
                         ffmpeg_command_0 + \
                         ffmpeg_command_1 + \
                         ffmpeg_command_2 + \
                         [ '-filter_complex', ffmpeg_filter ] + \
                         ffmpeg_params

        ffmpeg_command = ffmpeg_command + ['-y', temp_movie_name]
        # print(ffmpeg_command)
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

    # Now that all individuals clips are done, concatenate them all together.
    movie_filename = args.output
    if movie_filename is None or os.path.isdir(movie_filename):
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

    if len(dashcam_clips) == 1:
        # There really was only one, no need to create, just move
        # intermediate file.
        # Remove file 1st if it exist otherwise on Windows we can't rename.
        if os.path.isfile(movie_filename):
            try:
                os.remove(movie_filename)
            except OSError as exc:
                print("Error trying to remove file %s: %s", file, exc)

        if not args.keep_intermediate:
            try:
                shutil.move(dashcam_clips[0], movie_filename)
            except OSError as exc:
                print("Error trying to move file %s to %s: %s",
                      dashcam_clips[0],
                      movie_filename,
                      exc)
            else:
                print("Movie {base_name} has been created, enjoy.".format(
                    base_name=movie_filename))
        else:
            try:
                shutil.copyfile(dashcam_clips[0], movie_filename)
            except OSError as exc:
                print("Error trying to copy file %s to %s: %s",
                      dashcam_clips[0],
                      movie_filename,
                      exc)
            else:
                print("Movie {base_name} has been created, enjoy.".format(
                    base_name=movie_filename))

    elif len(dashcam_clips) > 1:
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

        if not args.keep_intermediate:
            for file in dashcam_clips:
                try:
                    os.remove(file)
                except OSError as exc:
                    print("Error trying to remove file %s: %s", file, exc)

    print()

sys.exit(main())
