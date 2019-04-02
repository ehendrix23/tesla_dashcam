tesla_dashcam
=============

Python program that provides an easy method to merge saved Tesla Dashcam footage into a single video.

When saving Tesla Dashcam footage a folder is created on the USB drive and within it multiple MP4 video files are
created. Currently the dashcam leverages three (3) cameras (front, left repeater, and right repeater) and will create a
file for each of them. Every minute is stored into a separate file as well. This means that when saving dashcam footage
there is a total of 30 files video files.

Using this Python program, one can combine all of these into 1 video file. The video of the three cameras is merged
into one picture, with the video for all the minutes further put together into one.

This is not limited to just the saved 10 minute footage. One can combine video files of different times footage
was saved into one folder and then run this program to have to all combined into one movie.

Binaries
--------

Stand-alone binaries can be retrieved:

- Windows: https://github.com/ehendrix23/tesla_dashcam/releases/download/0.1.8/tesla_dashcam.zip
- MacOS (OSX): https://github.com/ehendrix23/tesla_dashcam/releases/download/0.1.8/tesla_dashcam.dmg

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
solution to convert video.

`Python <https://www.python.org>`__ 3.5 or higher is required (unless stand-alone binaries are used).


Installation
-------------

This package is available from `pypi <https://pypi.org/project/tesla-dashcam/>`__. Installing it from there will ensure
other package requirements (except ffmpeg) are installed as well.

Install from pypi is done through:

.. code:: bash

    pip install tesla_dashcam



Usage
-----

.. code:: bash

    tesla_dashcam - Tesla DashCam Creator

    usage: tesla_dashcam.py [-h] [--version] [--output OUTPUT]
                            [--keep-intermediate]
                            [--layout {WIDESCREEN,FULLSCREEN,DIAGONAL,PERSPECTIVE}]
                            [--mirror | --rear] [--swap] [--no-swap]
                            [--slowdown SLOW_DOWN] [--speedup SPEED_UP]
                            [--encoding {x264,x265} | --enc ENC] [--no-gpu]
                            [--no-timestamp] [--halign {LEFT,CENTER,RIGHT}]
                            [--valign {TOP,MIDDLE,BOTTOM}] [--font FONT]
                            [--fontsize FONTSIZE] [--fontcolor FONTCOLOR]
                            [--quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}]
                            [--compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
                            [--ffmpeg FFMPEG]
                            source

    tesla_dashcam - Tesla DashCam Creator

    positional arguments:
      source                Folder containing the saved camera files.

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      --output OUTPUT       Path/Filename for the new movie file. Intermediate files will be stored in same folder.
                            If not provided then resulting movie files will be created within same folder as source files. (default: None)
      --keep-intermediate   Do not remove the intermediate video files that are
                            created (default: False)
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
      --swap                Swap left and rear cameras, default when layout
                            FULLSCREEN with --rear option is chosen. (default:
                            None)
      --no-swap             Do not swap left and rear cameras, default with all
                            other options. (default: None)
      --slowdown SLOW_DOWN  Slow down video output. Number is a multiplier,
                            providing 2 means half the speed. (default: None)
      --speedup SPEED_UP    Speed up the video. Number is a multiplier, providing
                            2 means twice the speed. (default: None)
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
                            within path. (default: ffmpeg)

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

.. code:: bash

    python3 tesla_dashcam.py -h

Using defaults:

* Windows:

.. code:: bash

    python3 tesla_dashcam.py c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 tesla_dashcam.py /Users/me/Desktop/Tesla/2019-02-27_14-02-03

Specify video file and location:

* Windows:

.. code:: bash

    python3 tesla_dashcam.py --output c:\Tesla\My_Video_Trip.mp4 c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 tesla_dashcam.py --output /Users/me/Desktop/Tesla/My_Video_Trip.mp4 /Users/me/Desktop/Tesla/2019-02-27_14-02-03

Without timestamp:

* Windows:

.. code:: bash

    python3 tesla_dashcam.py --no-timestamp c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 tesla_dashcam.py --no-timestamp /Users/me/Desktop/Tesla/2019-02-27_14-02-03


Put timestamp center top in yellowgreen:

* Windows:

.. code:: bash

    python3 tesla_dashcam.py --fontcolor yellowgreen@0.9 -halign CENTER -valign TOP c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 tesla_dashcam.py --fontcolor yellowgreen@0.9 -halign CENTER -valign TOP /Users/me/Desktop/Tesla/2019-02-27_14-02-03


Layout so front is shown top middle with side cameras below it and font size of 24 (FULLSCREEN):

* Windows:

.. code:: bash

    python3 tesla_dashcam.py --layout FULLSCREEN --fontsize 24 c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 tesla_dashcam.py --layout FULLSCREEN --fontsize 24 /Users/me/Desktop/Tesla/2019-02-27_14-02-03


Specify location of ffmpeg binay (in case ffmpeg is not in path):

* Windows:

.. code:: bash

    python3 tesla_dashcam.py --ffmpeg c:\ffmpeg\ffmpeg.exe c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 tesla_dashcam.py --ffmpeg /Applications/ffmpeg /Users/me/Desktop/Tesla/2019-02-27_14-02-03

Layout of FULLSCREEN with a different font for timestamp and path for ffmpeg:

* Windows: Note how to specify the path, : and \ needs to be escaped by putting a \ in front of them.

.. code:: bash

    python3 tesla_dashcam.py --layout FULLSCREEN --ffmpeg c:\ffmpeg\ffmpeg.exe --font "C\:\\Windows\\Fonts\\Courier New.ttf" c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 tesla_dashcam.py --layout FULLSCREEN --ffmpeg /Applications/ffmpeg --font '/Library/Fonts/Courier New.ttf' /Users/me/Desktop/Tesla/2019-02-27_14-02-03


Support
-------

There is no official support nor should there be any expectation for support to be provided. As per license this is
provided As-Is.
However, any issues or requests can be reported on `GitHub <https://github.com/ehendrix23/tesla_dashcam/issues>`__.


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



TODO
----

* Create self-contained executable for MacOS and Windows
* Support drag&drop of video folder
* Create GUI for options
* Option to specify resolutions as an argument
* Option for end-user layout
* Use timestamp in video to determine order instead of file name
* Use timestamp in video to ensure full synchronization between the 3 cameras
