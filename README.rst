.. image:: https://img.shields.io/github/downloads/ehendrix23/tesla_dashcam/total
   :target: https://img.shields.io/github/downloads/ehendrix23/tesla_dashcam/total
.. image:: https://img.shields.io/github/downloads/ehendrix23/tesla_dashcam/latest/total
   :target: https://GitHub.com/ehendrix23/tesla_dashcam/releases/
.. image:: https://img.shields.io/pypi/dm/tesla-dashcam
   :target: https://pypi.python.org/pypi/tesla-dashcam/

tesla_dashcam
=============

Python program that provides an easy method to merge saved Tesla Dashcam footage into a single video.

When saving Tesla Dashcam footage a folder is created on the USB drive for each event and within it multiple MP4 video files are
created. Currently the dashcam leverages four (4) cameras (front, rear, left repeater, and right repeater) and will create a
file for each of them. Every minute is stored into a separate file as well. This means that when saving dashcam footage
there is a total of 40 files video files for every 10 minutes, each event of 10 minutes is put into a separate folder.

Using this program, one can combine the 40 video files of an event into one (1), and combine video of multiple events together.
The layout of the four (4) different cameras within the resulting video can be determined by choosing one of the available layouts.

This program has multiple options providing a high level of flexibility on the videos to process, cameras to include,
layout of the resulting videos, location, format, encoding, .... See usage section below to read upon all the possibilities.

**Video Input** provides options related to the source videos.

*Trigger Monitor* is to have processing of videos not start upon execution of the program but instead be based on a trigger
(i.e. inserting the USB/SD card in the PC).

**Video Layout** provides parameters to define what the resulting video should look like. There are 4 different layouts to
choose from. This can then be further adjusted by having the left/right cameras be in perspective or not. Swap left/right
or front/rear cameras, change the scale for all cameras and/or for certain cameras, make left/right/rear seem as if you
were watching it through a mirror, or as if you turn your head around and looking backwards.

**Camera Exclusion** exclude certain cameras from the resulting video.

**Timestamp** options allow you to define what the timestamp in the resulting video should look like, or just to not have
it display at all.

**Timestamp Restriction** provides with the possibility to only create a video of the portion that are important. Instead
of uploading a video where the first 5 minutes is nothing, specify the start and end timestamps to shorten the video
to the important section instead.

**Event offsets** allows you to skip a portion from the start (and/or the end) for each event.

**Video Output** then further defines what the output should look like. Fast-forward through the Sentry video where nothing
is happening, speed up or slow down the video, ...

**Advanced encoding settings** allows you to further define additional encoding settings

And **Update Check** will make sure you always have the latest version available.

Check out the Usage section of this README to get more information on all available parameters and what each does.


Binaries
--------

Stand-alone binaries can be retrieved from:

- Windows: https://github.com/ehendrix23/tesla_dashcam/releases/latest/download/tesla_dashcam.zip
- MacOS (OSX): https://github.com/ehendrix23/tesla_dashcam/releases/latest/download/tesla_dashcam.dmg

`ffmpeg <https://www.ffmpeg.org/legal.html>`_ is included within the respective package.
ffmpeg is a separately licensed product under the `GNU Lesser General Public License (LGPL) version 2.1 or later <http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html>`_.
FFmpeg incorporates several optional parts and optimizations that are covered by the GNU General Public License (GPL) version 2 or later. If those parts get used the GPL applies to all of FFmpeg.
For more information on ffmpeg license please see: https://www.ffmpeg.org/legal.html

Windows binary of ffmpeg was downloaded from: https://ffmpeg.zeranoe.com/builds/

MacOS binary of ffmpeg was downloaded from: https://www.osxexperts.net


Notes
-----

The video files for the same minute between the 4 cameras are not always the same length. If there is a difference in
their duration then the background color (black by default) will be shown for the camera which video ended before the
others (within the minute).
It is thus possible within a video to see the background color for one of the cameras, and then when that minute has passed
for it to show video again.

The date and time shown within the video comes from the timestamp embedded in the saved videos themselves, not from the
filename. Date and time shown within resulting videos is converted to timezone set upon the PC it is being run on.


Requirements
-------------

This package relies on `ffmpeg <https://ffmpeg.org>`__ to be installed, this is a free, open source cross-platform
solution to convert video. The created executables for Windows and MacOS include an ffmpeg version.

If not using the executables (Windows and MacOS) then `Python <https://www.python.org>`__ 3.8.6 or higher is required.


Installation
-------------

Downloading the respective bundle (ZIP for Windows, DMG for MacOS) and unpacking this in a location of your choosing is
sufficient to install this.

If downloading the source files (i.e. for Linux) then Python has to be installed as well. I recommend in that case to
install the package from pypi using pip to ensure all package requirements (except for ffmpeg) are met.

This package is available from `pypi <https://pypi.org/project/tesla-dashcam/>`__.

Install from pypi is done through:

.. code:: bash

    python3 -m pip install tesla_dashcam



Usage
-----

.. code:: bash

    usage: tesla_dashcam.py [-h] [--version] [--loglevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--temp_dir TEMP_DIR] [--no-notification] [--display_ts] [--skip_existing]
                            [--delete_source] [--exclude_subdirs] [--monitor] [--monitor_once] [--monitor_trigger MONITOR_TRIGGER]
                            [--layout {WIDESCREEN,FULLSCREEN,PERSPECTIVE,CROSS,DIAMOND}] [--perspective] [--scale CLIP_SCALE [CLIP_SCALE ...]] [--mirror] [--rear] [--swap] [--no-swap]
                            [--swap_frontrear] [--background BACKGROUND] [--title_screen_map] [--no-front] [--no-left] [--no-right] [--no-rear] [--no-timestamp]
                            [--halign {LEFT,CENTER,RIGHT}] [--valign {TOP,MIDDLE,BOTTOM}] [--font FONT] [--fontsize FONTSIZE] [--fontcolor FONTCOLOR]
                            [--text_overlay_fmt TEXT_OVERLAY_FMT] [--timestamp_format TIMESTAMP_FORMAT] [--start_timestamp START_TIMESTAMP] [--end_timestamp END_TIMESTAMP]
                            [--start_offset START_OFFSET] [--end_offset END_OFFSET] [--sentry_offset] [--output OUTPUT] [--motion_only] [--slowdown SLOW_DOWN] [--speedup SPEED_UP]
                            [--chapter_offset CHAPTER_OFFSET] [--merge [MERGE_GROUP_TEMPLATE]] [--merge_timestamp_format MERGE_TIMESTAMP_FORMAT] [--keep-intermediate] [--keep-events]
                            [--set_moviefile_timestamp {START,STOP,SENTRY,RENDER}] [--no-gpu] [--gpu] [--gpu_type {nvidia,intel,rpi}] [--no-faststart]
                            [--quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}] [--compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}] [--fps FPS]
                            [--ffmpeg FFMPEG] [--encoding {x264,x265}] [--enc ENC] [--check_for_update] [--no-check_for_update] [--include_test]
                            [source [source ...]]

    tesla_dashcam - Tesla DashCam & Sentry Video Creator

    positional arguments:
      source                Folder(s) (events) containing the saved camera files. Filenames can be provided as well to manage individual clips. (default: None)

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      --loglevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                            Logging level. (default: INFO)
      --temp_dir TEMP_DIR   Path to store temporary files. (default: None)
      --no-notification     Do not create a notification upon completion. (default: True)
      --display_ts          Display timestamps on tesla_dashcam text output. DOES NOT AFFECT VIDEO OUTPUT. (default: False)

    Video Input:
      Options related to what clips and events to process.

      --skip_existing       Skip creating encoded video file if it already exist. Note that only existence is checked, not if layout etc. are the same. (default: False)
      --delete_source       Delete the processed files upon completion. (default: False)
      --exclude_subdirs     Do not search sub folders (events) for video files to process. (default: False)

    Trigger Monitor:
      Parameters for monitoring of insertion of TeslaCam drive, folder, or file existence.

      --monitor             Enable monitoring for drive to be attached with TeslaCam folder. (default: False)
      --monitor_once        Enable monitoring and exit once drive with TeslaCam folder has been attached and files processed. (default: False)
      --monitor_trigger MONITOR_TRIGGER
                            Trigger file to look for instead of waiting for drive to be attached. Once file is discovered then processing will start, file will be deleted when
                            processing has been completed. If source is not provided then folder where file is located will be used as source. (default: None)

    Video Layout:
      Set what the layout of the resulting video should be

      --layout {WIDESCREEN,FULLSCREEN,PERSPECTIVE,CROSS,DIAMOND}
                            Layout of the created video.
                                FULLSCREEN: Front camera center top, side cameras underneath it with rear camera between side camera.
                                WIDESCREEN: Front camera on top with side and rear cameras smaller underneath it.
                                PERSPECTIVE: Similar to FULLSCREEN but then with side cameras in perspective.
                                CROSS: Front camera center top, side cameras underneath, and rear camera center bottom.
                                DIAMOND: Front camera center top, side cameras below front camera left and right of front, and rear camera center bottom.
                            (default: FULLSCREEN)
      --perspective         Show side cameras in perspective. (default: False)
      --scale CLIP_SCALE [CLIP_SCALE ...]
                            Set camera clip scale for all clips, scale of 1 is 1280x960 camera clip.
                            If provided with value then it is default for all cameras, to set the scale for a specific camera provide camera=<front, left, right,rear> <scale>
                            for example:
                              --scale 0.5                                             all are 640x480
                              --scale 640x480                                         all are 640x480
                              --scale 0.5 --scale camera=front 1                      all are 640x480 except front at 1280x960
                              --scale camera=left .25 --scale camera=right 320x240    left and right are set to 320x240
                            Defaults:
                                WIDESCREEN: 1/2 (front 1280x960, others 640x480, video is 1920x1920)
                                FULLSCREEN: 1/2 (640x480, video is 1920x960)
                                CROSS: 1/2 (640x480, video is 1280x1440)
                                DIAMOND: 1/2 (640x480, video is 1920x976)
                            (default: None)
      --mirror              Video from side and rear cameras as if being viewed through the mirror. Default when not providing parameter --no-front. Cannot be used in combination with
                            --rear. (default: None)
      --rear                Video from side and rear cameras as if looking backwards. Default when providing parameter --no-front. Cannot be used in combination with --mirror. (default:
                            None)
      --swap                Swap left and right cameras in output, default when side and rear cameras are as if looking backwards. See --rear parameter. (default: None)
      --no-swap             Do not swap left and right cameras, default when side and rear cameras are as if looking through a mirror. Also see --mirror parameter (default: None)
      --swap_frontrear      Swap front and rear cameras in output. (default: False)
      --background BACKGROUND
                            Background color for video. Can be a color string or RGB value. Also see --fontcolor. (default: black)
      --title_screen_map    Show a map of the event location for the first 3 seconds of the event movie, when merging events it will also create map with lines linking the events (default: False)

    Camera Exclusion:
      Exclude one or more cameras:

      --no-front            Exclude front camera from video. (default: False)
      --no-left             Exclude left camera from video. (default: False)
      --no-right            Exclude right camera from video. (default: False)
      --no-rear             Exclude rear camera from video. (default: False)

    Text Overlay:
      Options on how to show text in resulting video:

      --no-timestamp        Do not show timestamp in video (default: False)
      --halign {LEFT,CENTER,RIGHT}
                            Horizontal alignment for timestamp (default: None)
      --valign {TOP,MIDDLE,BOTTOM}
                            Vertical Alignment for timestamp (default: None)
      --font FONT           Fully qualified filename (.ttf) to the font to be chosen for timestamp. (default: /Library/Fonts/Arial Unicode.ttf)
      --fontsize FONTSIZE   Font size for timestamp. Default is scaled based on resulting video size. (default: None)
      --fontcolor FONTCOLOR
                            Font color for timestamp. Any color is accepted as a color string or RGB value.
                            Some potential values are:
                                white
                                yellowgreen
                                yellowgreen@0.9
                                Red
                            :    0x2E8B57
                            For more information on this see ffmpeg documentation for color: https://ffmpeg.org/ffmpeg-utils.html#Color (default: white)
      --text_overlay_fmt TEXT_OVERLAY_FMT
                            Format string for text overlay.
                            Valid format variables:
                                {clip_start_timestamp} - Local time the clip starts at
                                {clip_end_timestamp} - Local time the clip ends at
                                {local_timestamp_rolling} - Local time which continuously updates (shorthand for '%{{pts:localtime:{local_timestamp}:%x %X}}'), string
                                {event_timestamp} - Timestamp from events.json (if provided), string
                                {event_timestamp_countdown_rolling} - Local time which continuously updates (shorthand for '%{{hms:localtime:{event_timestamp}}}'), string
                                {event_city} - City name from events.json (if provided), string
                                {event_reason} - Recording reason from events.json (if provided), string
                                {event_latitude} - Estimated latitude from events.json (if provided), float
                                {event_longitude} - Estimated longitude from events.json (if provided), float
                                
                                All valid ffmpeg 'text expansion' syntax is accepted here.
                                More info: http://ffmpeg.org/ffmpeg-filters.html#Text-expansion
                            (default: {local_timestamp_rolling})
      --timestamp_format TIMESTAMP_FORMAT
                            Format for timestamps.
                            Determines how timestamps should be represented. Any valid value from strftime is accepted.Default is set '%x %X' which is locale's appropriate date and time representationMore info: https://strftime.org (default: %x %X)

    Timestamp Restriction:
      Restrict video to be between start and/or end timestamps. Timestamp to be provided in a ISO-8601 format (see https://fits.gsfc.nasa.gov/iso-time.html for examples)

      --start_timestamp START_TIMESTAMP
                            Starting timestamp (default: None)
      --end_timestamp END_TIMESTAMP
                            Ending timestamp (default: None)

    Event offsets:
      Start and/or end offsets for events

      --start_offset START_OFFSET
                            Skip x number of seconds from start of event for resulting video. Default is 0 seconds, 60 seconds if --sentry_offset is provided. (default: None)
      --end_offset END_OFFSET
                            Ignore the last x seconds of the event for resulting video. Default is 0 seconds, 30 seconds if --sentry_offset is provided. (default: None)
      --sentry_offset       start_offset and end_offset will be based on when timestamp of object detection occurred for Sentryevents instead of start/end of event. (default: False)

    Video Output:
      Options related to resulting video creation.

      --output OUTPUT       Path/Filename for the new movie file. Event files will be stored in same folder.
                            (default: /Users/ehendrix/Movies/Tesla_Dashcam/)
      --motion_only         Fast-forward through video when there is no motion. (default: False)
      --slowdown SLOW_DOWN  Slow down video output. Accepts a number that is then used as multiplier, providing 2 means half the speed.
      --speedup SPEED_UP    Speed up the video. Accepts a number that is then used as a multiplier, providing 2 means twice the speed.
      --chapter_offset CHAPTER_OFFSET
                            Offset in seconds for chapters in merged video. Negative offset is # of seconds before the end of the subdir video, positive offset if # of seconds after the
                            start of the subdir video. (default: 0)
      --merge [MERGE_GROUP_TEMPLATE]
                            Merge the video files from different folders (events) into 1 big video file.
                            Optionally add a template string to group events in different video files based on the template.
                            Valid format variables:
                                {layout} - Layout of the created movie (see --layout)
                                {start_timestamp} - Local time the event started at
                                {end_timestamp} - Local time the event ends at        
                                {event_timestamp} - Timestamp from events.json (if provided), string
                                {event_city} - City name from events.json (if provided), string
                                {event_reason} - Recording reason from events.json (if provided), string
                                {event_latitude} - Latitude from events.json (if provided), float
                                {event_longitude} - Longitude from events.json (if provided), float        
      --merge_timestamp_format MERGE_TIMESTAMP_FORMAT
                            Format for timestamps in merge_template.
                            Determines how timestamps should be represented within merge_template. Any valid value from strftime is accepted.Default is set '%Y-%m-%d_%H_%M'More info: https://strftime.org (default: %Y-%m-%d_%H_%M)
      --keep-intermediate   Do not remove the clip video files that are created (default: False)
      --keep-events         Do not remove the event video files that are created when merging events into a video file (see --merge) (default: False)
      --set_moviefile_timestamp {START,STOP,SENTRY,RENDER}
                            Match modification timestamp of resulting video files to event timestamp. Use START to match with when the event started, STOP for end time of the event,
                            SENTRY for Sentry event timestamp, or RENDER to not change it. (default: START)

    Advanced encoding settings:
      Advanced options for encoding

      --no-gpu              Disable use of GPU acceleration. Default on Apple Silicon Mac and on Non-MACs.                            
      --gpu                 Use GPU acceleration. Default on Intel Macs.
                            Note: ffmpeg currently seems to have issues on Apple Silicon with GPU acceleration, --no-gpu might need to be set to produce video.
                            --gpu_type has to be provided as well on Non-Macs when enabling this parameter (default: False)
      --gpu_type {nvidia,intel,rpi}
                            Type of graphics card (GPU) in the system. This determines the encoder that will be used.This parameter is mandatory if --gpu is provided on Non-Macs. (default: None)
      --no-faststart        Do not enable flag faststart on the resulting video files. Use this when using a network share and errors occur during encoding. (default: False)
      --quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}
                            Define the quality setting for the video, higher quality means bigger file size but might not be noticeable. (default: LOWER)
      --compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                            Speed to optimize video. Faster speed results in a bigger file. This does not impact the quality of the video, just how much time is used to compress it.
                            (default: medium)
      --fps FPS             Frames per second for resulting video. Tesla records at about 33fps hence going higher wouldn't do much as frames would just be duplicated. Default is 24fps
                            which is the standard for movies and TV shows (default: 24)
      --ffmpeg FFMPEG       Path and filename for ffmpeg. Specify if ffmpeg is not within path. (default: /Users/ehendrix-
                            personal/Documents_local/GitHub/tesla_dashcam/tesla_dashcam/ffmpeg)
      --encoding {x264,x265}
                            Encoding to use for video creation.
                                x264: standard encoding, can be viewed on most devices but results in bigger file.
                                x265: newer encoding standard but not all devices support this yet.
      --enc ENC             Provide a custom encoder for video creation. Cannot be used in combination with --encoding.
                            Note: when using this option the --gpu option is ignored. To use GPU hardware acceleration specify an encoding that provides this.

    Update Check:
      Check for updates

      --check_for_update    Check for update and exit. (default: False)
      --no-check_for_update
                            A check for new updates is performed every time. With this parameter that can be disabled (default: False)
      --include_test        Include test (beta) releases when checking for updates. (default: False)

Positional Argument
-------------------

Source does not have a specific parameter. Just provide the folder(s) to be scanned and processed. One can provide
folder(s) and/or file(s) here. Source is not mandatory, if not provided then the default will be SavedClips and SentryClips.
The path searches for SavedClips and SentryClips will depend if there was a Trigger Monitor parameter provided or not.
If source is not provided and no Trigger Monitor provided then --monitor_once will be enabled with SavedClips and SentryClips.


Optional Arguments
------------------

These are some other optional arguments that don't change in what will be processed, how, layout, resulting video file
or so.

*-h or --help*

  Show the help message and exit.

*--version*

  Show the version number of the program and exit.

*--loglevel <level>*

  Log level for additional output. Currently only used for DEBUG, providing any other value will not change anything.

*--temp_dir <path>*

  Temporary path to store the temporary (intermediate) clip video files. When processing a temporary video file is
  created for each minute within an event folder combining the different cameras together. Then these temporary video
  files are merged together to produce the resulting event video file. By default the temporary clip video files will
  be stored in the same folder as specified where the resulting video file will be stored. Using this parameter one
  can thus specify another folder instead. Can be especially helpful when the resulting videos are being stored on
  a network share as one can then specify a local drive that would be faster for the temporary files.

*--no-notification*

  Upon completion a notification is provided on the screen that processing is completed. Use this parameter to
  disable this notification.

  *--display_ts*

  Add timestamp to the text output procuded.

Video Input
-----------

Following options are to manage what should be processed and what to do once processed.

*--skip_existing*

  Default: False

  By default if a resulting video files already exist then it will be overwritten (except with --monitor). By providing this
  parameter if the resulting video file already exist then it will not be recreated. Note that this only checks for existence
  of the video file and not if the layout etc. of that video file matches current selection.

*--delete_source*

  Default: False

  Delete the clips (files) and events (folders) on the source once processing has been completed.

*--exclude_subdirs*

  Default: False

  Do not scan any subfolders within the source provided for valid clips.


Trigger Monitor
---------------

When the program is executed the provide source folders are being scanned for events and clip files, processed, and
then the program exits. Using these parameters it is possible however to start the program before the SD or USB has been
inserted and have it wait. It can then be set to wait again after first time processing or to stop.

*--monitor*

  Default: False

  Monitor for drive to be attached that has the TeslaCam folder in its root. If not already one attached then wait till
  one is attached. Once a drive with the TeslaCam folder is attached processing will start based on the source provided.
  If no source was provided then all events within SavedClips and SentryClips will be processed instead. To have it
  process all 3 folders then provide the following for source:

  SavedClips SentryClips RecentClips

  After processing the program will wait until the drive has been ejected from the system. Once ejected it will
  start monitoring again for a drive to be attached. This loop will continue until stopped with CTRL-C.

*--monitor_once*

  Default: False

  This is the same as --monitor however instead of waiting for the drive to be ejected after processing the program
  will stop.

*--monitor_trigger <File or folder>*

  Monitor for existence of a folder (or file) instead of a drive with TeslaCam folder. Once the file (or folder) exist
  then processing will start. If source is provided then that will be used for scanning for events and clips. If no
  source was provided then the path provided for this parameter will be used as source instead. If the provided source
  is a relative path (i.e. Tesla/MyVideos) then it will be relative based on the location of the trigger file/path.

  Upon completion, if a trigger file was provided then that file will be deleted and the program will wait again
  until the trigger file exist again. If a trigger folder was provided then the program will wait until this folder
  has been removed. Then it will start monitoring again for existence for this folder.


Video Layout
------------

The layout of the resulting video can be adjusted in many ways through multiple parameters. Parameter --layout
specifies where each camera clip should be placed within the resulting video. (see above for examples).

*--layout*

  Default: FULLSCREEN

* FULLSCREEN: Resolution: 1920x960

::

    +---------------+----------------+----------------+
    |               | Front Camera   |                |
    +---------------+----------------+----------------+
    | Left Camera   |  Rear Camera   |  Right Camera  |
    +---------------+----------------+----------------+

Video example: https://youtu.be/P5k9PXPGKWQ


* WIDESCREEN: Resolution: 1920x1920

::

    +---------------+----------------+----------------+
    |                 Front Camera                    |
    +---------------+----------------+----------------+
    | Left Camera   |  Rear Camera   |  Right Camera  |
    +---------------+----------------+----------------+

Video example: https://youtu.be/nPleIhVxyhQ


* CROSS: Resolution: 1280x1440

::

    +---------------+----------------+----------------+
    |               | Front Camera   |                |
    +---------------+----------------+----------------+
    |     Left Camera      |       Right Camera       |
    +---------------+----------------+----------------+
    |               | Rear Camera    |                |
    +---------------+----------------+----------------+


* DIAMOND: Resolution: 1920x976

::

    +---------------+----------------+----------------+
    |               |  Front Camera  |                |
    +---------------+                +----------------+
    |   Left Camera |----------------| Right Camera   |
    +               +  Rear Camera   +                +
    |---------------|                |----------------|
    +---------------+----------------+----------------+


*--perspective*

  Default: False

  Show the side cameras in perspective mode.


*--scale*

  This can then be further adjusted by changing the scale for all cameras or changing the scale for one or more making
  them smaller or bigger then the others. This is done with the --scale parameter. If just provided with a number then
  scale is multiplied based on that number.

  For example, 0.5 results in 640x480 as standard resolution is 1280x960. Or one can also provide the resolution instead
  of the scale. For example providing 640x480. Changing the scale can be done for specific cameras as well. This is
  done by preceding the scale number (or resolution) with camera=<camera> where <camera> can be front, rear, left,
  or right. One can provide the --scale parameter multiple times.

  For example:

  \-\-scale 1 --scale camera=left .25 --scale camera=right 640x480

  results in front and rear camera clips to be of size 1280x960, left camera would be 320x240, and right camera would
  be 640x480.


*--mirror or --rear*

  By default the left, right, and rear cameras are shown as if one is sitting inside the car and looking through the
  mirrors. However, if the front camera is not included (with option --no-front) then this is changed making it seem
  as if one is looking backwards and not through a mirror. With option --mirror or --rear one can override the default
  for this.

  Using --rear you can thus make it so that it is shown as if looking backwards yet still having the front one shown.
  Same, using --mirror one can make it as if the view is shown through a mirror without showing the front camera.

*--swap or --no-swap*

  Default is to swap left and right cameras (left one is shown on the right in the video and right one is shown on the left)
  when they are viewed as if looking backwards (see --rear). Using --no-swap this can then be overridden.


  Similar, when looking as if through a mirror the default is not to swap left and right cameras. With --swap this can be
  overridden.

*--swap_frontrear*

  Default: False

  Using this you can swap the front and the rear camera in the layouts. The front camera is normally on top with the rear
  camera being at the bottom. With this the front camera will be shown at the bottom and the rear on the top.

*--background*

  Default: Black

  Specify the background color for the video. Default is black. See --fontcolor for possible values.

  *--title_screen_map*

  Default: False

  Show a map of the event location for the first 3 seconds within the event. When merging multiple events an additional map will
  be created for the start of the movie showing locations of all events within the movie linked with lines.
  Note, if merging multiple events within a movie then a map will be shown at the start of each event within that movie.

Camera Exclusion
----------------

By default the output from all 4 cameras is shown within the merged video if existing. Using these parameters one can
exclude one or more cameras from the resulting video.

*--no-front*

  Default: False

  Exclude the front camera from the resulting video.

*--no-left*

  Default: False

  Exclude the left camera from the resulting video.

*--no-right*

  Default: False

  Exclude the right camera from the resulting video.

*--no-rear*

  Default: False

  Exclude the rear camera from the resulting video.

Text Overlay
------------

Following parameters are to change settings for the text that is being added to the resulting video.

*--text_overlay_fmt*

  Default: {local_timestamp_rolling}

  Sets the format string for the text overlayed in the video. Use \n to specify a newline.
  Valid format specifiers:
  
  `{local_timestamp_rolling}`: Local time which continuously updates, string

  `{local_timestamp}`: Local time that does not continuously update, string

  `{event_timestamp}`: Timestamp from events.json (if provided), string

  `{event_city}`: City name from events.json (if provided), string

  `{event_reason}`: Recording reason from events.json (if provided), string

  `{event_latitude}`: Estimated latitude from events.json (if provided), float

  `{event_longitude}`: Estimated longitude from events.json (if provided), float


*--timestamp_format*

  Default: %x %X

  Set how timestamps should be formatted. See https://strftime.org on how to use this. Default represents date and time in current locale's format.

*--no-timestamp*

  Default: False

  Do not display timestamp within the resulting video.

*--halign*

  Default: CENTER

  Determine the horizontal alignment of the timestamp within the resulting video. The default for this normally
  is to display the timestamp in the center of the video. Exception to this is for DIAMOND layout when excluding
  left or right camera in which case the horizontal placement of the font is adjusted so that it is still displayed
  between the front and rear camera. The alignment can be overridden with:

  LEFT: place timestamp to the left of the video

  CENTER: place timestamp in the center of the video

  RIGHT: place timestamp to the right of the video

*--valign*

  Default: BOTTOM

  Set the vertical alignment of the timestamp within the resulting video. Default is at the bottom of the video except
  for layout DIAMOND where it is in the middle to be placed in the space between the front and rear camera.

  TOP: place timestamp at the top of the video

  MIDDLE: place timestamp in the middle of the video

  BOTTOM: place timestamp at the bottom of the video

*--font <filename>*

  Override the default font for the timestamp. Filename/path provided here has to be a fully qualified filename to the
  font file (.ttf).

*--fontsize <size>*

  Font size for the timestamp. Default font size is scaled based on the resulting video size, use this to override and
  provide a fix font size.

*--fontcolor <color*

  Default: white

  The color for the timestamp as a color string or RGB value. More information on how to provide the color can be
  found here: `https://ffmpeg.org/ffmpeg-utils.html#Color <https://ffmpeg.org/ffmpeg-utils.html#Color>`_

  Some possible values are:
    white

    yellowgreen

    yellowgreen@0.9

    Red

    0x2E8B57


Timestamp Restriction
---------------------

The events/clips to be processed and thus be put in the resulting video can be restricted by providing a start and/or
end timestamp.

The timestamps provided do not need to match the start or end timestamp of a specific event or specific clip. Video within
the clip will be skipped if it falls outside of the timestamp.

By default the timestamp will be interpreted based on the timezone of the PC the program runs on. This can be
overridden however.

The timestamp is to be provided based on the ISO-8601 format (see
`https://fits.gsfc.nasa.gov/iso-time.html <https://fits.gsfc.nasa.gov/iso-time.html>`_) for description and examples of
this format.

In general, the date is provided in the format YYYY, YYYY-MM, YYYY-MM-DD, YYYY-Wxx, YYYY-ddd

Here are some examples:

  2019 to process restrict video to year 2019.

  2019-09 for September, 2019.

  2019-09-10 or 20190910 for 10th of September, 2019

  2019-W37 (or 2019W37) for week 37 in 2019

  2019-W37-2 (or 2019W372) for Tuesday (day 2) of Week 37 in 2019

  2019-253 (or 2019253) for day 253 in 2019 (which is 10th of September, 2019)

To identify the time, one can use hh, hh:mm, or hh:mm:ss.
If providing both a date and a time then these are seperated using the letter T:

  2019-09-10T11:15:10 for 11:15AM on the 10th of September, 2019.

Timezone for the timestamp can be provided as well.
  For UTC time add the letter Z to the time: 2019-09-10T11:15:10Z for 11:15AM on the 10th of September, 2019 UTC time.

One can also use +hh:mm, +hhmm, +hh, -hh:mm, -hhmm, -hh to use a different timezone.

  2019-09-10T11:15:10-0500 is for 11:15AM on the 10th of September, 2019 EST.

For further guidance on potential values see: https://www.cl.cam.ac.uk/~mgk25/iso-time.html

*--start_timestamp <timestamp>*

  Starting timestamp to include in resulting video. Anything before this timestamp will be skipped (even when inside
  the clip containing the starting timestamp).

*--end_timestamp <timestamp>*

  Ending timestamp to include in resulting video. Anything after this timestamp will be skipped (even when inside
  the clip containing the ending timestamp).

Event offsets
-------------

This is to skip forward or stop earlier within an event. The skipping is done for each event (folder) individually.
For example, one can set it to skip the 1st 5 minutes of each event by providing the --start_offset 300 (300 seconds = 5 minutes).
Provided offsets are calculated before any video adjustments such as speeding up, slowing down, or motion only. Offsets
can work in combination with the timestamp restriction however the offsets will always be calculated based on the event
start and end timestamps. Thus if the start timestamp is set to be 2 minutes into the event, and the offset is set to 5 minutes
then the resulting video will start 5 minutes in (and not 7 minutes into the event). If the start timestamp is 3 minutes into
the event, and the starting offset is set to 2 minutes then the resulting video will start at 3 minutes in. Same
methodology is applied for ending offset and end timestamp.

When enabling --sentry_offset then the offsets only operate on events that were recorded due to a Sentry event.
The offsets are then based on the event timestamp (timestamp that triggered Sentry to save the event) and not the start/end timestamp of the event.
For this it is possible to provide positive or negative values. When providing a negative value for start_offset then the clip
will start before the event timestamp. When providing a positive value then it will be after the event start.
Similar, when providing a negative value for end_offset the ending of the clip will be before the event, and with
a positive value it will be after the event.

*--start_offset <offset>*

  Starting offset within the event. <offset> is in seconds.

*--end_offset <offset>*

  Ending offset within the event. <offset> is in seconds.

*--senty_offset*

  Default: False

  Start and end offsets will be based on the timestamp that triggered the Sentry event instead of the start and end timestamps of the event.
  
Video Output
------------

These are additional parameters related to the resulting video creation.

*--output <path/filename>*

  Path/filename for the resulting video. If a filename is provided here and --merge is set then the resulting merged
  video will be saved with this filename. The event videos will be stored within the same folder. To just provide a filename, 
  but keeping the default folder based on platform, add an extension to the name. For example, providing "event" will create 
  the files in folder event, but providing "event.mp4" will instead create the movie file event.mp4 in the default folder.
  
*--motion_only*

  Default: False

  Resulting video will show fast forwarded video for any portion where there is no or very little motion. This can
  be especially useful for Sentry events since those are 10-minute events but often only have a few minutes (if that)
  of useful activity in it that resulted in the event being created.

*--slowdown <speed>*

  Slow the resulting video down by provided multiplier. For example, a <speed> of 2 would mean that the video
  will be half the speed of normal.

*--speedup <speed>*

  Increase the speed of the resulting video by provided multiplier. For example, a value of 2 means that the video
  will be going twice the normal speed.

*--chapter_offset <seconds>*

  Sets an offset for the chapter markers in the merged video. By default a chapter marker is set at the start of each
  event within the merged video. Using this one can set the chapter marker <seconds> before or after the start of the event.

  Providing a negative value here results in the chapter marker being set x number of seconds before the end of the event.

  Providing a positive value results in the chapter marker being set x number of seconds after the start of the event.

*--merge*

  Default: False

  A video file is created for each event (folder) found. When parameter --merge is provided these individual event
  video files will then be further merged into 1 bigger video file. 
  Optionally add a template string to group events together and create multiple video files. Resulting video filename will be based on this template.
  See --text_overlay_fmt for format variables.
 
*--merge_timestamp_format*

  Default: %Y-%m-%d_%H_%M

  Determine how timestamps should be represented within the template provided for --merge.
  For example:

  To merge events in a movies grouped by date/hour:

      --merge "{event_timestamp}" --merge_timestamp_format "%Y-%m-%d_%H"
  
  To merge events in a movies grouped by date:

      --merge "{event_timestamp}" --merge_timestamp_format "%Y-%m-%d"
  

*--keep-intermediate*

  Default: False

  Temporary video files are being created during the processing of the events. These temporary video files are the
  combined camera clips for 1 minute, and thus normally 10 of these video files are created (one for each minute).
  These files are then deleted once the event is processed and the event video file has been created. Use this
  parameter to keep these temporary video files instead. Note that depending on the number of events a lot more
  storage will be required then.

*--keep-events*

  Default: False

  When set the event video files that were generated will not be deleted after they have been merged into a video file (see --merge). 
  If this is not set then the event video files will be automatically deleted upon successful creation of the merged video file.

*--set_moviefile_timestamp*

  Default: START

  Determine what the modification timestamp on the OS for resulting video file should be set at. START will set it at the start of the event, 
  STOP for the end of the event, SENTY for the timestamp that triggered the SENTRY event (if no SENTRY timestamp then will go back to START),
  or RENDER to not modify the timestamp resulting in it being when the movie was created.

Advanced Encoding Settings
--------------------------

The following parameters are more advanced settings to determine how ffmpeg should encode the videos.

*--no-gpu*

  Disables GPU acceleration. 
  Intel Macs: GPU acceleration is enabled by default, use this parameter to disable it.
  Apple Silicon Macs: GPU acceleration is disabled by default due to current issues with ffmpeg.
  Non-Macs: GPU acceleration is disabled by default.

  If this parameter is used in combination with --gpu then the first one will have preference.

  Note: we can only detect Apple Silicon if Python deployed is the Universal2 binary OR the tesla_dashcam executable is for Apple Silicon.
  If running on Apple Silicon but using the x64 executable or x64 Python then tesla_dashcam will not be able to detect it is running on Apple Silicon.

*--gpu*

  Enables GPU acceleration.
  Intel Macs: this is already enabled by default
  Apple Silicon Macs: to enable GPU acceleration. Note that current ffmpeg produces a corrupt video when doing this but newer versions of ffmpeg might work.
  Non-Macs: to enable GPU acceleration, parameter parameter --gpu_type has to be provided as well then to identify the hardware.

  If this parameter is used in combination with --no-gpu then the first one will have preference.

  Note: we can only detect Apple Silicon if Python deployed is the Universal2 binary OR the tesla_dashcam executable is for Apple Silicon.
  If running on Apple Silicon but using the x64 executable or x64 Python then tesla_dashcam will not be able to detect it is running on Apple Silicon.

*--gpu_type*

  All platforms except Macs. Provide the GPU type installed in the system.

    intel: if INTEL GPU is installed

    nvidia: if NVIDIA GPU is installed

    rpi: on Raspberry Pi systems

*--no-faststart*

   Default: False

   By default the ffmpeg flag faststart is set. Doing this will ensure that certain meta data is placed at the start
   of the resulting video which then improves streaming (i.e. YouTube, WebSites, ...). This parameter is to disable
   this and thus having the meta data placed at the end of the video file (which is normal default). This can improve
   performance as video files will not have to be rewritten after processing to put the metadata at the beginning of the
   file, and it can also prevent issues with video files are located on a network share.

*--quality*

  Default: LOWER

  Set the overall quality for the resulting video. Setting this to a higher value can improve the quality (not guaranteed)
  but most likely will also result in bigger file sizes. Resulting improvement might not be noticeable.

    Valid values: LOWEST, LOWER, LOW, MEDIUM, HIGH

*--compression*

  Default: medium

  Defines how much time should be spend to compress the resulting video file. Slower speed can result in improved
  compression of the video file and thus a smaller video size. However it would also result in longer processing time.

    ultrafast will result in least amount of time processing to compress the video file, but largest video size.

    veryslow will result in the smallest video file, but the longest amount of time to create the video file.

  Note that increasing or decreasing compression time will not impact the quality of the resulting video. Just the
  resulting file size.

    Valid values: ultrafast, superfast,veryfast,faster,fast,medium,slow,slower,veryslow

*--fps <frames>*

  Default: 24

  Set the frames per seconds for the resulting video. Default frames per second for movies and TV shows is 24fps. Tesla
  cameras are recording and saving at about 33fps. Using default about 9 frames per second are dropped from the resulting
  video. With this parameter the fps for the resulting video can be adjusted. Set it to 33 to keep the number of frames
  similar to Tesla's. Setting this value higher would just result in frames being duplicated. For example, setting it to
  66 would mean that for every second, each frame is duplicated to get from 33fps to 66fps.

*--ffmpeg <executable>*

  For Windows and MacOS an executable is delivered with FFMPEG build-in. When using this executable this parameter
  can be easily ignored unless one wants to specify a different ffmpeg version then what is delivered.

  On all other platforms (or on Windows and MacOS when not using the executable) ffmpeg has to be downloaded and
  installed separately. If ffmpeg is within the search path (on most platforms defined through environment variable PATH)
  then there is also no reason to provide this. If ffmpeg is not within the search path (or one wants to use a different
  ffmpeg then what is provided in the executable) then one can provide the fully qualified name for the ffmpeg to be used.

*--encoding*

  Default: x264

  Provide the encoding for the resulting video. Default is x264 as today this is still the most common format for
  video files. One can also encode it in x265 which is the newer video standard. Encoding in x265 results in a smaller
  video file however certain programs or platforms might not be able to view this yet. Use x264 if providing the
  video to a wide audience, you can use x265 for private usage and ability to view x265.

    Valid values: x264, x265

*--enc <encoder>*

  ffmpeg uses an encoder to create (encode) the video files. By default the encoder selected is based on platform
  (Windows, Mac, Linux), GPU acceleration and GPU type, and encoding (x264, x265). With this parameter it is possible
  to provide a different encoder instead to create the video file. For further information please see the ffmpeg
  documentation on video encoders. The value provided here will be provided to parameter c:v <encoder>

Update Check
------------

A check to determine if a newer version is available will be performed every time the program is executed. These
parameters allow you to influence this.

*--check_for_update*

  Check if there is a new update available and then just exit. This allows you to perform the check without processing
  anything.

*--no-check_for_update*

  Default: False

  Do not perform the check if there is an update available. Not recommended as no checks are performed, but can be
  used when there is no internet available, slow internet, ...

*--include_test*

  Default: False

  Include test (beta) releases when checking for new updates. If this parameter is provided then it will also include
  any beta releases. Note that it has to be an actual beta releases within releases. Sometimes the development branch
  can have releases that have not been released as a test release.


Argument (Parameter) file
-------------------------

A lot of different parameters can be provided, thus to make it easier one can have these parameters within a text file
and then supply this text file instead of having to enter them each time on the command line. Combination of
having parameters in a text file and supplying it together with additional parameters on the command line is possible
as well. This thus allows having multiple text files based on different preferences (i.e. layouts, ...) and still
provide other parameters (i.e. start_timestamp and end_timestamp) on the command line.

Arguments within the text file can all be on one (1) line, on separate lines, or a combination thereof. Use # to identify
comments. Everything behind # on a line is then ignored.
Note, on Windows the argument specifying the parameter file has to be between double quotes (")

Having a text file (i.e. my_preference.txt) with the following contents:

.. code:: bash

    --speedup 10 --rear
    --merge --output /home/me/Tesla
    --monitor_once SavedClips

And then executing tesla_dashcam as follows:

* Windows:

.. code:: bash

    tesla_dashcam.exe "@my_preference.txt"

* Mac:

.. code:: bash

    tesla_dashcam @my_preference.txt

* Linux:

.. code:: bash

    python3 tesla_dashcam.py @my_preference.txt

Would result in the same as if those parameters were provided on the command itself. One can also combine a parameter file with parameters on the command line.
Preference is given to what occurs first. For example, if providing the following arguments:

.. code:: bash

    --speedup 2 @my_preference.txt

Then the clips will only be sped up two-fold instead of 10-fold as --speedup 2 occurs before --speedup 10 from the parameter file.
But with:

.. code:: bash

    @my_preference.txt --speedup 2

the clips will be sped up ten-fold.

Examples
--------

To show help:

* Windows:

.. code:: bash

    tesla_dashcam.exe -h

* Mac:

.. code:: bash

    tesla_dashcam -h

* Linux:

.. code:: bash

    python3 tesla_dashcam.py -h


Using defaults:

* Windows:

.. code:: bash

    tesla_dashcam.exe c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    tesla_dashcam /Users/me/Desktop/Tesla/2019-02-27_14-02-03

* Linux:

.. code:: bash

    python3 tesla_dashcam.py /home/me/Tesla/2019-02-27_14-02-03

Using defaults but not knowing what to provide for source path. Goal to only process the SavedClips and only do this once.
Store the resulting video files in c:\Tesla (Windows) or /Users/me/Desktop/Tesla (MacOS). Delete the files from the
USB (or SD) when processed.

* Windows:

.. code:: bash

    tesla_dashcam.exe --monitor_once --delete_source --output c:\Tesla SavedClips

* Mac:

.. code:: bash

    tesla_dashcam --monitor_once --delete_source --output /Users/me/Desktop/Tesla SavedClips

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --monitor_once --delete_source --output /home/me/Tesla SavedClips

Specify video file and location:

* Windows:

.. code:: bash

    tesla_dashcam.exe --output c:\Tesla\My_Video_Trip.mp4 c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    tesla_dashcam --output /Users/me/Desktop/Tesla/My_Video_Trip.mp4 /Users/me/Desktop/Tesla/2019-02-27_14-02-03

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --output /home/me/Tesla/My_Video_Trip.mp4 /home/me/Tesla/2019-02-27_14-02-03

Without timestamp:

* Windows:

.. code:: bash

    tesla_dashcam.exe --no-timestamp c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    tesla_dashcam --no-timestamp /Users/me/Desktop/Tesla/2019-02-27_14-02-03

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --no-timestamp /home/me/Tesla/2019-02-27_14-02-03

Put timestamp center top in yellowgreen:

* Windows:

.. code:: bash

    tesla_dashcam.exe --fontcolor yellowgreen@0.9 -halign CENTER -valign TOP c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    tesla_dashcam --fontcolor yellowgreen@0.9 -halign CENTER -valign TOP /Users/me/Desktop/Tesla/2019-02-27_14-02-03

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --fontcolor yellowgreen@0.9 -halign CENTER -valign TOP /home/me/Tesla/2019-02-27_14-02-03

Layout so front is shown top middle with side cameras below it and font size of 24 (FULLSCREEN):

* Windows:

.. code:: bash

    tesla_dashcam.exe --layout FULLSCREEN --fontsize 24 c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    tesla_dashcam --layout FULLSCREEN --fontsize 24 /Users/me/Desktop/Tesla/2019-02-27_14-02-03

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --layout FULLSCREEN --fontsize 24 /home/me/Tesla/2019-02-27_14-02-03

Specify location of ffmpeg binay (in case ffmpeg is not in path):

* Windows:

.. code:: bash

    tesla_dashcam.exe --ffmpeg c:\ffmpeg\ffmpeg.exe c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    tesla_dashcam --ffmpeg /Applications/ffmpeg /Users/me/Desktop/Tesla/2019-02-27_14-02-03

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --ffmpeg /home/me/ffmpeg /home/me/Tesla/2019-02-27_14-02-03

Layout of PERSPECTIVE with a different font for timestamp and path for ffmpeg:

* Windows: Note how to specify the path, : and \ needs to be escaped by putting a \ in front of them.

.. code:: bash

    tesla_dashcam.exe --layout PERSPECTIVE --ffmpeg c:\ffmpeg\ffmpeg.exe --font "C\:\\Windows\\Fonts\\Courier New.ttf" c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    tesla_dashcam --layout PERSPECTIVE --ffmpeg /Applications/ffmpeg --font '/Library/Fonts/Courier New.ttf' /Users/me/Desktop/Tesla/2019-02-27_14-02-03

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --layout PERSPECTIVE --ffmpeg /Applications/ffmpeg --font '/usr/share/fonts/truetype/freefont/Courier New.ttf' /home/me/Tesla/2019-02-27_14-02-03

Enable monitoring for the Tesla Dashcam USB (or SD) to be inserted and then process all the files (both RecentClips and SavedClips).
Increase speed of resulting videos tenfold and store all videos in folder specified by output.
Delete the source files afterwards:


.. code:: bash

    tesla_dashcam.exe --speed 10 --output c:\Tesla\ --monitor .

* Mac:

.. code:: bash

    tesla_dashcam /Users/me/Desktop/Tesla --monitor .

* Linux:

.. code:: bash

    python3 tesla_dashcam.py /home/me/Desktop/Tesla --monitor .


Enable one-time monitoring for the Tesla Dashcam USB (or SD) to be inserted and then process all the files from SavedClips.
Note that for source we provide the folder name (SavedClips), the complete path will be created by the program.
Slowdown speed of resulting videos to half, show left/right cameras as if looking backwards, store all videos in folder specified by output.
Also create a movie file that has them all merged together.

* Windows:

.. code:: bash

    tesla_dashcam.exe --slowdown 2 --rear --merge --output c:\Tesla\ --monitor_once SavedClips

* Mac:

.. code:: bash

    tesla_dashcam --slowdown 2 --rear --merge --output /Users/me/Desktop/Tesla --monitor_once SavedClips

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --slowdown 2 --rear --merge --output /home/me/Tesla --monitor_once SavedClips

Enable monitoring using a trigger file (or folder) to start processing all the files from SavedClips.
Note that for source we provide the folder name (SavedClips), the complete path will be created by the program using the
path of the trigger file (if it is a file) or folder. Videos are stored in folder specified by --output. Videos from all
the folders are then merged into 1 folder with name TeslaDashcam followed by timestamp of processing (timestamp is
added automatically). Chapter offset is set to be 2 minutes (120 seconds) before the end of the respective folder clips.

* Windows:

.. code:: bash

    tesla_dashcam.exe --merge --chapter_offset -120 --output c:\Tesla\TeslaDashcam.mp4 --monitor --monitor_trigger x:\TeslaCam\start_processing.txt SavedClips

* Mac:

.. code:: bash

    tesla_dashcam --merge --chapter_offset -120 --output /Users/me/Desktop/Tesla --monitor --monitor_trigger /Users/me/TeslaCam/start_processing.txt SavedClips

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --merge --chapter_offset -120 --output /home/me/Tesla --monitor --monitor_trigger /home/me/TeslaCam/start_processing.txt SavedClips


Support
-------

There is no official support nor should there be any expectation for support to be provided. As per license this is
provided As-Is.
However, any issues or requests can be reported on `GitHub <https://github.com/ehendrix23/tesla_dashcam/issues>`__ and
I will do my best (time permitting) to provide support.


Release Notes
-------------

0.1.4:
    - Initial Release
0.1.5:
    - Fixed: font issue on Windows
0.1.6:
    - Changed: Output folder is now optional
    - Changed: Source is positional argument (in preparation for self-contained executable and drag&drop)
0.1.7:
    - New: Added perspective layout (thanks to `lairdb <https://model3ownersclub.com/members/lairdb.16314/>`__ from `model3ownersclub <https://model3ownersclub.com>`__ forums to provide this layout).
    - New: Added font size option to set the font size for timestamp
    - New: Added font color option to set the font color for timestamp
    - New: Added halign option to horizontally align timestamp (left, center, right)
    - New: Added valign option to vertically align timestamp (top, middle, bottom)
    - Changed: Perspective is now default layout.
0.1.8:
    - New: Added GPU hardware accelerated encoding for Mac and PCs with NVIDIA. On Mac it is enabled by default
    - New: Added option to have video from side cameras be shown as if one were to look at it through the mirror (option --mirror). This is now the default
    - New: Added option --rear to show video from side cameras as if one was looking to the rear of the car. This was how it was originally.
    - New: Added option to swap left and right camera in output. Mostly beneficial in FULLSCREEN with --rear option as it then seems like it is from a rear camera
    - New: Added option to speedup (--speedup) or slowdown (--slowdown) the video.
    - New: Added option to provide a different encoder for ffmpeg to use. This is for those more experienced with ffmpeg.
    - New: Added a default font path for Linux systems
    - New: Added --version to get the version number
    - New: Releases will now be bundled in a ZIP file (Windows) or a DMG file (MacOS) with self-contained executables in them. This means Python does not need to be installed anymore (located on github)
    - New: ffmpeg executable binary for Windows and MacOS added into respective bundle.
    - Changed: For output (--output) one can now also just specify a folder name. The resulting filename will be based on the name of the folder it is then put in
    - Changed: If there is only 1 video file for merging then will now just rename intermediate (or copy if --keep-intermediate is set).
    - Changed: The intermediate files (combining of the 3 cameras into 1 video file per minute) will now be written to the output folder if one provided.
    - Changed: The intermediate files will be deleted once the complete video file is created. This can be disabled through option --keep-intermediate
    - Changed: Set FULLSCREEN back as the default layout
    - Changed: Help output (-h) will show what default value is for each parameter
    - Changed: Cleaned up help output
    - Changed: Default path for ffmpeg will be set to same path as tesla_dashcam is located in, if not exist then default will be based that ffmpeg is part of PATH.
    - Fixed: Now able to handle if a camera file is missing, a black screen will be shown for that duration for the missing file
    - Fixed: Fixed (I believe) cygwin path for fonts.
0.1.9:
    - New: Added scanning of sub-folders clip files. Each folder will be processed and resulting movie file created. This can be disabled through parameter --exclude_subdirs
    - New: Added option to merge the video files from multiple sub-folders into 1 movie file. Use parameter --merge to enable.
    - New: Added option to monitor if the USB drive (or SD card) is inserted in the PC and then automatically start processing the files. Use parameter --monitor to enable.
      Parameter --monitor_once will stop monitoring and exit after 1st time drive was inserted.
      Parameter --delete_source will delete the source files and folder once the movie file for that folder has been created.
    - New: Added update checker to determine if there is a newer version, additional arguments to just perform check (--check_for_update), include test releases (--include_test), or disable always checking for updates (--no-check_for_update)
    - New: ffmpeg is part of the tesla_dashcam executable
    - New: Desktop notification when processing starts (when using monitor) and when it completes.
    - New: DockerFile added making it easy to run tesla_dashcam within Docker (jeanfabrice)
    - New: Time it took to create the video files will now be provided upon completion of processing.
    - Changed: Formatted output to easily show progress
    - Fixed: Will now handle it much better if a video file from a camera is corrupt (i.e. zero-byte file).
    - Fixed: combining clips to movie would not use GPU or provided encoding.
    - Fixed: Added additional check that video file exist before merging into movie.
0.1.10:
    - New: Added scale option to set the scale of the clips and thus resulting video. (--scale)
    - New: Added option to specify a parameter file using @<filename> where parameters can be located in. (@<filename>)
    - New: One can now specify multiple sources instead of just 1.
    - New: Individual file(s) can now be provided as a source as well (only 1 camera filename has to be provided to get all 3)
    - New: Source is now optional, if not provided then it will be same as --monitor_once with as source SavedClips.
    - Changed: Timestamp within video will now be used for concatenation of the clips at folder level and all (--merge option) instead of filename. This will ensure that even when crossing timezones the order of the video is still accurate.
    - Changed: --delete_source will delete source files when specified even when --monitor or --monitor_once is not specified `Issue #28 <https://github.com/ehendrix23/tesla_dashcam/issues/28>`_
    - Changed: output will default to Videos\Tesla_Dashcam (Windows) Movies/Tesla_Dashcam (MacOS), or Videos\Tesla_Dashcam (Linux) if not output folder specified.
    - Changed: Filename for the folder video files will not have start and end timestamp in local timezone instead of just folder name. `Issue #30 <https://github.com/ehendrix23/tesla_dashcam/issues/30>`_ and `Issue #33 <https://github.com/ehendrix23/tesla_dashcam/issues/33>`_
    - Changed: Updated release notes for each release better identifying what is new, changed, and fixed.
    - Fixed: issue where sometimes encoding with GPU would fail by also allowing software based encoding
    - Fixed: traceback when unable to retrieve latest release from GitHub
    - Fixed: running tesla_dashcam when installed using pip. `Issue #23 <https://github.com/ehendrix23/tesla_dashcam/issues/23>`_ and `Issue #31 <https://github.com/ehendrix23/tesla_dashcam/issues/31>`_
    - Fixed: Folder clip would be removed if only 1 set in folder with same name as folder name if keep_intermediate not specified
    - Fixed: Font issue in Windows (hopefully final fix) `Issue #29 <https://github.com/ehendrix23/tesla_dashcam/issues/29>`_
    - Fixed: Python version has to be 3.7 or higher due to use of capture_output `Issue #19 <https://github.com/ehendrix23/tesla_dashcam/issues/19>`_
0.1.11:
    - Fixed: Traceback when getting ffmpeg path in Linux `Issue #39 <https://github.com/ehendrix23/tesla_dashcam/issues/39>`_
    - Fixed: Running tesla_dashcam when installed using pip. `Issue #38 <https://github.com/ehendrix23/tesla_dashcam/issues/38>`_
    - Fixed: Just providing a filename for output would result in traceback.
    - Fixed: When providing a folder as output it would be possible that the last folder name was stripped potentially resulting in error.
0.1.12:
    - New: Added chapter markers in the concatenated movies. Folder ones will have a chapter marker for each intermediate clip, merged one has a chapter marker for each folder.
    - New: Option --chapter_offset for use with --merge to offset the chapter marker in relation to the folder clip.
    - New: Added flag -movstart +faststart for video files better suited with browsers etc. (i.e. YouTube). Thanks to sf302 for suggestion.
    - New: Option to add trigger (--monitor_trigger_file) to use existence of a file/folder/link for starting processing instead of USB/SD being inserted.
    - Changed: Method for concatenating the clips together has been changed resulting in massive performance improvement (less then 1 second to do concatenation). Big thanks to sf302!
    - Fixed: Folders will now be deleted if there are 0-byte or corrupt video files within the folder `Issue #40 <https://github.com/ehendrix23/tesla_dashcam/issues/40>`_
    - Fixed: Providing a filename for --output would create a folder instead and not setting resulting file to filename provided `Issue #52 <https://github.com/ehendrix23/tesla_dashcam/issues/52>`_
    - Fixed: Thread exception in Windows that ToastNotifier does not have an attribute classAtom (potential fix). `Issue #54 <https://github.com/ehendrix23/tesla_dashcam/issues/54>`_
    - Fixed: Traceback when invalid output path (none-existing) is provided or when unable to create target folder in given path.
    - Fixed: Including sub dirs did not work correctly, it would only grab the 1st folder.
    - Fixed: When using monitor, if . was provided as source then nothing would be processed. Now it will process everything as intended.
    - Fixed: File created when providing a filename with --output and --monitor option did not put timestamp in filename to ensure unique filenames
    - Fixed: Argument to get release notes was provided incorrectly when checking for updates. Thank you to demonbane for fixing.
0.1.13:
    - New: Support for rear camera (introduced in V10). This also results in layouts having been modified to allow inclusion of rear camera. `Issue #71 <https://github.com/ehendrix23/tesla_dashcam/issues/71>`_
    - New: Support for hardware encoding for systems with supported Intel GPUs.
    - New: Support for hardware encoding on Raspberry Pi (RPi) (H.264 only) `Issue #66 <https://github.com/ehendrix23/tesla_dashcam/issues/66>`_
    - New: Layout CROSS with front camera top centered, side camera underneath it, and rear camera then underneath side cameras centered.
    - New: Layout DIAMOND with front camera top centered, rear camera under front and side camera centered at the left and right of front&rear.
    - New: Option --motion_only to fast-forward through the portions in the video that does not have anything motion (done through removal of duplicate frames). Thanks to supRy for providing this
    - New: Option --skip_existing to skip creation of video files that already exist. Existence only is checked, not if layout etc are the same.
    - New: Option --perspective for showing side cameras to be displayed in perspective mode irrespective of layout. Layout PERSPECTIVE is thus same as layout FULLSCREEN with --perspective option.
    - New: Options --start_offset and --end_offset can be used to provide starting and ending offset in seconds for resulting video (at folder level).
    - New: Options --start_timestamp and --end_timestamp can be used to restrict resulting video (and processing) to specific timestamps. This can be used in combination with --start_offset and/or --end_offset
    - New: Options --no-front, --no-left, --no-right, and --no-rear to exclude camera(s) from the videos
    - New: Option --gpu_type to provide GPU installed in the system for Windows/Linux. Current supported options are nvidia, intel, and RPi.
    - New: Option  --no-faststart for not setting the faststart flag in the video files as doing this can result in encoding failures on network shares `Issue #62 <https://github.com/ehendrix23/tesla_dashcam/issues/62>`_
    - New: Option --temp_dir to provide a different path to store the temporary video files that are created `Issue #67 <https://github.com/ehendrix23/tesla_dashcam/issues/67>`_
    - New: Description metadata to include video was created by tesla_dashcam with version number.
    - Changed: WIDESCREEN layout will now by default show the front camera on top with higher resolution compared to others due to incorporation of rear camera
    - Changed: Include folder SentryClips in default source list if no source provided (SavedClips was already default).
    - Changed: Check to ensure that Python version is at required level or higher (currently 3.7).
    - Changed: Existence of font file (provided or default) will be checked and error returned if not existing.
    - Changed: Existence of ffmpeg will be checked and error returned if not existing.
    - Changed: If no filename provided for merged video then current date/time will be used for filename.
    - Fixed: Merge of videos fails when a relative path instead of an absolute path is provided for --output `Issue #62 <https://github.com/ehendrix23/tesla_dashcam/issues/62>`_
    - Fixed: Issue during processing of metadata if files were missing
    - Fixed: Hidden files (files starting with period) on Mac/Linux were not ignored. This could cause issues as some programs might create these files when viewing the video.
0.1.14:
    - Fixed: Checking if font path exist in Windows failed.
0.1.15:
    - Changed: Reduced sensitivity for motion detection
    - Changed: Minor improvement for font path checking, mainly message provided.
    - Fixed: Rear view camera filename was changed from -rear_view to -back in TeslaCam folders. `Issue #78 <https://github.com/ehendrix23/tesla_dashcam/issues/78>`_
    - Fixed: Missing python-dateutil package when installing from PIP `Issue #77 <https://github.com/ehendrix23/tesla_dashcam/issues/77>`_
    - Fixed: Missing fonts in Docker Image (thanks to moorecp for providing fix)
    - Fixed: Only the 1st source was processed When using MONITOR or MONITOR_ONCE, or with V10 only SavedClips was processed when not providing a source
0.1.16:
    - New: Option --scale now accepts value of camera=<front, rear, left, right>. to set the scale of for each camera individually (value of 1 is 1280x960 for the clip)
    - New: Option --swap_frontrear to swap front&rear cameras in output.
    - New: Option --background to specify background color (default is black).
    - New: Option --fps to set the frame rate for resulting video. Default is set to 24 (Tesla records at about 33 fps). `Issue #85 <https://github.com/ehendrix23/tesla_dashcam/issues/85>`_
    - New: Parameter file (provided using @) can now include comments (specify using #)
    - New: Option --loglevel to allow for debug information to be printed.
    - Changed: --speedup and --slowdown now accepts a float allowing for example to speed video up by 1.5
    - Changed: Option --scale also accept fixed resolution (i.e. 640x480) for the clip.
    - Changed: View of rear camera will be mirrored as well if side cameras are shown as mirror
    - Changed: For all layouts default is to show mirror for rear&side if front camera is shown, otherwise show as rear viewing.
    - Changed: Swap left&right cameras when showing rear&side as rear viewing, and not to swap them when showing rear&side as mirror view.
    - Changed: Re-organized help (-h) for all parameters by grouping them.
    - Changed: Added message to install fonts using apt-get install ttf-freefont on Linux if font file is not found.
    - Changed: Only execute if we're main allowing to be imported into other scripts. `Issue #94 <https://github.com/ehendrix23/tesla_dashcam/issues/94>`_
    - Changed: Cleaned-up this README file to provide better information.
    - Fixed: Providing paths with spaces did not work in parameter files even although it worked from command line. `Issue #89 <https://github.com/ehendrix23/tesla_dashcam/issues/89>`_
    - Fixed: Changed Arial font on MacOS to Arial Unicode (from Arial) as it seems Arial is not available anymore on MacOS 10.15 (Catalina). `Issue #64 <https://github.com/ehendrix23/tesla_dashcam/issues/64>`_
    - Fixed: Incorrect encoder for x265 with Intel GPU hardware encoding - mbaileys
0.1.17:
    - New: Option --text_overlay_fmt to set the overlay text for the video. Contributed by JakeShirley
    - New: Option --timestamp_format for formatting timestamps.
    - New: Option --sentry_offset to set the start and end offset based on Sentry event timestamp.
    - New: Option --merge_template to allow merging of video files grouped based on this. Resulting movie filename will be based on this template.
    - New: Option --set_moviefile_timestamp to set the video file timestamp on the OS to start, end, or time of Sentry event.
    - New: Option --keep-events to keep event video files after they have been merged into a video.
    - New: Option --display_ts to show timestamps in the text output. This does not impact video output but is handy when using a monitor option. Contributed by croadfeldt
    - New: Option --title_screen_map, which generates a map of the event location and displays it for the first 3 seconds of the movie.
    - New: Added support for event information file and ability to display it in the overlay text. Contributed by JakeShirley
    - New: Support for FreeBSD 11. Contributed by busbyjon
    - New: Source can now include wildcards, shell variables, and will do user expansion (i.e. ~ on Unix, ~user on Windows).
    - New: Output and temp_dir can now include shell variables and will do user expansion (i.e. ~ on Unix, ~user on Windows).
    - New: Metadata tag title in video file is now set to reason for event (if exist) and timestamp or start/end timestamp
    - New: Metadata tag creation_time in video files created is now set to start timestamp of that particular video.
    - New: When scanning folders a message will be printed after every 10 folders scanned to show progress.
    - New: --gpu and --no-gpu are now valid arguments irrespective of platform.  
    - New: event and final movie files will now include GPS coordinates with the location for an event. For movies this will be for the 1st event within the movie.
    - Changed: Improvement for Docker file size and stability. Contributed by magicalyak
    - Changed: Choice values for parameters (i.e. FULLSCREEN, intel, black) are now case-insensitive.
    - Changed: Updated supporting libraries to latest available.
    - Fixed: When providing an invalid start or end timestamp will now result in a error instead of a traceback.
    - Fixed: Added x265 compatibility tag for QuickTime. Contributed by dburkland
    - Fixed: Event file will now be removed when providing an output file and only 1 event is processed, leaving only 1 movie file.
    - Fixed: Providing a mount as a source resulted in it no files found. Now when a mount is provided it will be handled same as folders.
0.1.18:
    - Fixed: Traceback when running executable without providing --ffmpeg option.


TODO
----

* Implement option to crop individual camera output
* Option for end-user layout
* Monitor path for new folders/files as trigger option
* Provide option to copy or move from source to output folder before starting to process
* Develop method to run as a service with --monitor option
* GUI Front-end
* Support drag&drop of video folder (supported in Windows now, MacOS not yet)
* Add object detection (i.e. people) and possible output when object was detected
* Saving of options
* Use timestamp in video to ensure full synchronization between the 4 cameras
* Add option for source/output to be S3 bucket (with temp folder for creating temporary files)
* Develop Web Front-End
* Develop method to have run in AWS, allowing user to upload video files and interact using Web Front-End

