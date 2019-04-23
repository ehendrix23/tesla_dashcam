tesla_dashcam
=============

Python program that provides an easy method to merge saved Tesla Dashcam footage into a single video.

When saving Tesla Dashcam footage a folder is created on the USB drive and within it multiple MP4 video files are
created. Currently the dashcam leverages three (3) cameras (front, left repeater, and right repeater) and will create a
file for each of them. Every minute is stored into a separate file as well. This means that when saving dashcam footage
there is a total of 30 files video files for every 10 minutes. Each block of 10 minutes is put into a folder, thus often
there will be multiple folders.

Using this Python program, one can combine all of these into 1 video file. The video of the three cameras is merged
into one picture, with the video for all the minutes further put together into one.

By default sub-folders are included when retrieving the video clips. One can, for example, just provide the path to the
respective SavedClips folder (i.e. e:\TeslaCam\SavedClips for Windows if drive has letter E,
/Volumes/Tesla/TeslaCam/SavedClips on MacOS if drive is mounted on /Volumes/Tesla) and then all folders that were created
within the SavedClips folder will be processed. There will be a movie file for each folder.
When using the option --merge there will also be a movie file created combining the movies from all the folders into 1.
Use parameter --exclude_subdirs to only scan the folder provided and not any of the sub-folders.

There is also the option to monitor for a disk to become available with the TeslaCam folder on it. Video files will be
automatically processed once the USB (or SD) drive has been inserted. After processing the program will wait again until
this drive has been ejected and then a new one is inserted at which point it will start processing again (unless
--monitor_once parameter was used in which case the program will exit).
Note processing will occur if the drive is already inserted and the program is then started with this option.

When using the --monitor (or --monitor_once) option, video files from a folder will not be re-processed if the movie
file for that folder already exist.
It is still possible for --monitor_once to provide a output filename instead of just a folder. For --monitor the filename
will be ignored and the files will be created within the path specified using a unique name instead.

When using --merge, the name of the resulting video file will be appended with the current timestamp of processing when
--monitor parameter is used, this to ensure that the resulting video file is always unique.

If --merge is not provided as an option and there are multiple sub-folders then the filename (if provided in output)
will be ignored. Instead the files will all be placed in the folder identified by the output parameter, one movie file
for each folder. Only exception to this if there was only 1 folder.


Binaries
--------

Stand-alone binaries can be retrieved:

- Windows: https://github.com/ehendrix23/tesla_dashcam/releases/download/v0.1.9/tesla_dashcam.zip
- MacOS (OSX): https://github.com/ehendrix23/tesla_dashcam/releases/download/v0.1.9/tesla_dashcam.dmg

`ffmpeg <https://www.ffmpeg.org/legal.html>`_ is included within the respective package.
ffmpeg is a separately licensed product under the `GNU Lesser General Public License (LGPL) version 2.1 or later <http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html>`_.
FFmpeg incorporates several optional parts and optimizations that are covered by the GNU General Public License (GPL) version 2 or later. If those parts get used the GPL applies to all of FFmpeg.
For more information on ffmpeg license please see: https://www.ffmpeg.org/legal.html

Windows binary of ffmpeg was downloaded from: https://ffmpeg.zeranoe.com/builds/

MacOS binary of ffmpeg was downloaded from: https://evermeet.cx/ffmpeg/


Notes
-----

The video files for the same minute between the 3 cameras are not always the same length. If there is a difference in
their duration then a black screen will be shown for the camera which video ended before the others (within the minute).
It is thus possible within a video to see a black screen for one of the cameras, and then when that minute has passed
for it to show video again.

The date and time shown within the video comes from the timestamp embedded in the saved videos themselves, not from the
filename. Date and time shown within video is based on PC's timezone.
Tesla embeds the date and time within the video file, and that is what will be displayed comes. This means that the video might
not start exactly at 0 seconds. In the provided video examples one can see that it starts at 16:42:35 and not 16:42:00.

Current caveat however is that the order for concatenating all the videos together is based on filename. (See TODO)

Requirements
-------------

This package relies on `ffmpeg <https://ffmpeg.org>`__ to be installed, this is a free, open source cross-platform
solution to convert video. The ZIP (Windows) and DMG (MacOS) includes this package.

`Python <https://www.python.org>`__ 3.5 or higher is required (unless ZIP (Windows) or DMG (MacOS) packages are used).


Installation
-------------

Downloading the respective bundle (ZIP for Windows, DMG for MacOS) and unpacking this in a location of your choosing is
sufficient to install this.

If downloading the source files (i.e. for Linux) then Python has to be installed as well. I recommend in that case to
install the package from pypi using pip to ensure all package requirements (except for ffmpeg) are met.

This package is available from `pypi <https://pypi.org/project/tesla-dashcam/>`__.

Install from pypi is done through:

.. code:: bash

    pip install tesla_dashcam



Usage
-----

.. code:: bash

    usage: tesla_dashcam [-h] [--version] [--exclude_subdirs | --merge]
                         [--output OUTPUT] [--keep-intermediate]
                         [--layout {WIDESCREEN,FULLSCREEN,DIAGONAL,PERSPECTIVE}]
                         [--mirror | --rear] [--swap] [--no-swap]
                         [--slowdown SLOW_DOWN] [--speedup SPEED_UP]
                         [--encoding {x264,x265} | --enc ENC] [--no-gpu]
                         [--no-timestamp] [--halign {LEFT,CENTER,RIGHT}]
                         [--valign {TOP,MIDDLE,BOTTOM}] [--font FONT]
                         [--fontsize FONTSIZE] [--fontcolor FONTCOLOR]
                         [--quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}]
                         [--compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
                         [--ffmpeg FFMPEG] [--monitor] [--monitor_once]
                         [--delete_source] [--check_for_update]
                         [--no-check_for_update] [--include_test]
                         source

    tesla_dashcam - Tesla DashCam & Sentry Video Creator

    positional arguments:
      source                Folder containing the saved camera files.

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      --exclude_subdirs     Do not search all sub folders for video files to.
                            (default: False)
      --merge               Merge the video files from different folders into 1
                            big video file. (default: False)
      --output OUTPUT       Path/Filename for the new movie file. Intermediate files will be stored in same folder.
                            If not provided then resulting movie files will be created within same folder as source files. (default: None)
      --keep-intermediate   Do not remove the intermediate video files that are
                            created (default: False)
      --no-notification     Do not create a notification upon completion.
                            (default: False)
      --layout {WIDESCREEN,FULLSCREEN,DIAGONAL,PERSPECTIVE}
                            Layout of the created video.
                                FULLSCREEN: Front camera center top, side cameras underneath it.
                                WIDESCREEN: Output from all 3 cameras are next to each other.
                                PERSPECTIVE: Front camera center top, side cameras next to it in perspective.
                             (default: FULLSCREEN)
      --mirror              Video from side cameras as if being viewed through the
                            sidemirrors. Cannot be used in combination with
                            --rear. (default: True)
      --rear                Video from side cameras as if looking backwards.
                            Cannot be used in combination with --mirror. (default:
                            False)
      --swap                Swap left and right cameras, default when layout
                            FULLSCREEN with --rear option is chosen. (default:
                            None)
      --no-swap             Do not swap left and right cameras, default with all
                            other options. (default: None)
      --slowdown SLOW_DOWN  Slow down video output. Accepts a number that is then
                            used as multiplier, providing 2 means half the speed.
                            (default: None)
      --speedup SPEED_UP    Speed up the video. Accepts a number that is then used
                            as a multiplier, providing 2 means twice the speed.
                            (default: None)
      --encoding {x264,x265}
                            Encoding to use for video creation.
                                x264: standard encoding, can be viewed on most devices but results in bigger file.
                                x265: newer encoding standard but not all devices support this yet.
                             (default: x264)
      --enc ENC             Provide a custom encoding for video creation.
                            Note: when using this option the --gpu option is ignored. To use GPU hardware acceleration specify a encoding that provides this. (default: None)
      --no-gpu              Use GPU acceleration, only enable if supported by hardware.
                             MAC: All MACs with Haswell CPU or later  support this (Macs after 2013).
                                  See following link as well:
                                     https://en.wikipedia.org/wiki/List_of_Macintosh_models_grouped_by_CPU_type#Haswell
                             Windows and Linux: PCs with NVIDIA graphic cards support this as well.
                                                For more information on supported cards see:
                                     https://developer.nvidia.com/video-encode-decode-gpu-support-matrix (default: False)
      --ffmpeg FFMPEG       Path and filename for ffmpeg. Specify if ffmpeg is not
                            within path. (default: /Users/ehendrix/Documents/GitHu
                            b/tesla_dashcam/bundles/MacOS/tesla_dashcam/ffmpeg)

    Timestamp:
      Options for timestamp:

      --no-timestamp        Include timestamp in video (default: False)
      --halign {LEFT,CENTER,RIGHT}
                            Horizontal alignment for timestamp (default: CENTER)
      --valign {TOP,MIDDLE,BOTTOM}
                            Vertical Alignment for timestamp (default: BOTTOM)
      --font FONT           Fully qualified filename (.ttf) to the font to be
                            chosen for timestamp. (default:
                            /Library/Fonts/Arial.ttf)
      --fontsize FONTSIZE   Font size for timestamp. (default: 16)
      --fontcolor FONTCOLOR
                            Font color for timestamp. Any color is accepted as a color string or RGB value.
                            Some potential values are:
                                white
                                yellowgreen
                                yellowgreen@0.9
                                Red
                            :    0x2E8B57
                            For more information on this see ffmpeg documentation for color: https://ffmpeg.org/ffmpeg-utils.html#Color (default: white)

    Video Quality:
      Options for resulting video quality and size:

      --quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}
                            Define the quality setting for the video, higher
                            quality means bigger file size but might not be
                            noticeable. (default: LOWER)
      --compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                            Speed to optimize video. Faster speed results in a
                            bigger file. This does not impact the quality of the
                            video, just how much time is used to compress it.
                            (default: medium)

    Monitor for TeslaDash Cam drive:
      Parameters to monitor for a drive to be attached with folder TeslaCam in
      the root.

      --monitor             Enable monitoring for drive to be attached with
                            TeslaCam folder. (default: False)
      --monitor_once        Enable monitoring and exit once drive with TeslaCam
                            folder has been attached and files processed.
                            (default: False)
      --delete_source       Delete the processed files on the TeslaCam drive.
                            (default: False)

    Update Check:
      Check for updates

      --check_for_update    Check for updates, do not do anything else. (default:
                            False)
      --no-check_for_update
                            A check for new updates is performed every time. With
                            this parameter that can be disabled (default: False)
      --include_test        Include test (beta) releases when checking for
                            updates. (default: False)




Layout:
-------

`FULLSCREEN:` Resolution: 1280x960
::

    +---------------+----------------+
    |           Front Camera         |
    +---------------+----------------+
    | Left Camera   |  Right Camera  |
    +---------------+----------------+

Video example: https://youtu.be/P5k9PXPGKWQ

`PERSPECTIVE:` Resolution: 980x380
::

    +---------------+----------------+---------------+
    | Diagonal Left | Front Camera   | Diagonal Right|
    | Camera        |                | Camera        |
    +---------------+----------------+---------------+

Video example: https://youtu.be/fTUZQ-Ej5AY


`WIDESCREEN:` Resolution: 1920x480
::

    +---------------+----------------+---------------+
    | Left Camera   | Front Camera   | Right Camera  |
    +---------------+----------------+---------------+

Video example: https://youtu.be/nPleIhVxyhQ




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


.. code:: bash

    tesla_dashcam.exe --slowdown 2 --rear --merge --output c:\Tesla\ --monitor_once SavedClips

* Mac:

.. code:: bash

    tesla_dashcam --slowdown 2 --rear --merge --output /Users/me/Desktop/Tesla --monitor_once SavedClips

* Linux:

.. code:: bash

    python3 tesla_dashcam.py --slowdown 2 --rear --merge --output /home/me/Tesla --monitor_once SavedClips

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
    - Fixed font issue on Windows
0.1.6:
    - Output folder is now optional
    - source is positional argument (in preparation for self-contained executable and drag&drop)
0.1.7:
    - Added perspective layout (thanks to `lairdb <https://model3ownersclub.com/members/lairdb.16314/>`__ from `model3ownersclub <https://model3ownersclub.com>`__ forums to provide this layout).
    - Perspective is now default layout.
    - Added font size option to set the font size for timestamp
    - Added font color option to set the font color for timestamp
    - Added halign option to horizontally align timestamp (left, center, right)
    - Added valign option to vertically align timestamp (top, middle, bottom)
0.1.8:
    - Added GPU hardware accelerated encoding for Mac and PCs with NVIDIA. On Mac it is enabled by default
    - Added option to have video from side cameras be shown as if one were to look at it through the mirror (option --mirror). This is now the default
    - Added option --rear to show video from side cameras as if one was looking to the rear of the car. This was how it was originally.
    - Added option to swap left and right camera in output. Mostly beneficial in FULLSCREEN with --rear option as it then seems like it is from a rear camera
    - Added option to speedup (--speedup) or slowdown (--slowdown) the video.
    - Added option to provide a different encoder for ffmpeg to use. This is for those more experienced with ffmpeg.
    - Now able to handle if a camera file is missing, a black screen will be shown for that duration for the missing file
    - For output (--output) one can now also just specify a folder name. The resulting filename will be based on the name of the folder it is then put in
    - If there is only 1 video file for merging then will now just rename intermediate (or copy if --keep-intermediate is set).
    - The intermediate files (combining of the 3 cameras into 1 video file per minute) will now be written to the output folder if one provided.
    - The intermediate files will be deleted once the complete video file is created. This can be disabled through option --keep-intermediate
    - Set FULLSCREEN back as the default layout
    - Added a default font path for Linux systems
    - Fixed (I believe) cygwin path for fonts.
    - Help output (-h) will show what default value is for each parameter
    - Cleaned up help output
    - Added --version to get the version number
    - Releases will now be bundled in a ZIP file (Windows) or a DMG file (MacOS) with self-contained executables in them. This means Python does not need to be installed anymore (located on github)
    - ffmpeg executable binary for Windows and MacOS added into respective bundle.
    - Default path for ffmpeg will be set to same path as tesla_dashcam is located in, if not exist then default will be based that ffmpeg is part of PATH.
0.1.9:
    - Added scanning of sub-folders clip files. Each folder will be processed and resulting movie file created. This can be disabled through parameter --exclude_subdirs
    - Added option to merge the video files from multiple sub-folders into 1 movie file. Use parameter --merge to enable.
    - Added option to monitor if the USB drive (or SD card) is inserted in the PC and then automatically start processing the files. Use parameter --monitor to enable.
      Parameter --monitor_once will stop monitoring and exit after 1st time drive was inserted.
      Parameter --delete_source will delete the source files and folder once the movie file for that folder has been created.
    - Added update checker to determine if there is a newer version, additional arguments to just perform check (--check_for_update), include test releases (--include_test), or disable always checking for updates (--no-check_for_update)
    - Formatted output to easily show progress
    - Time it took to create the video files will now be provided upon completion of processing.
    - Will now handle it much better if a video file from a camera is corrupt (i.e. zero-byte file).
    - ffmpeg is part of the tesla_dashcam executable
    - Desktop notification when processing starts (when using monitor) and when it completes.

TODO
----

* Add object detection (i.e. people) and possible output when object was detected
* Support drag&drop of video folder
* GUI Front-end
* Saving of options
* Option to specify resolutions as an argument
* Option for end-user layout
* Use timestamp in video to determine order instead of file name
* Use timestamp in video to ensure full synchronization between the 3 cameras
