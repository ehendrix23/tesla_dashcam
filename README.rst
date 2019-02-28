tesla_dashcam
=============

Python program that provides an easy method to merge saved Tesla Dashcam footage into a single video.

When saving Tesla Dashcam footage a folder is created on the USB drive and within it multiple MP4 video files are
created. Currently the dashcam leverages three (3) cameras (front, left repeater, and right repeater) and will create a
file for each of them. Every minute is stored into a seperate file as well. This means that when saving dashcam footage
there is a total of 30 files video files.

Using this Python program, one can combine all of these into 1 video file. The video of the three cameras is merged
into one picture, with the video for all the minutes further put together into one.

This is not limited to just the saved 10 minute footage. One can combine video files of different times footage
was saved into one folder and then run this program to have to all combined into one movie.

Requirements
-------------

This package relies on `ffmpeg <https://ffmpeg.org>`__ to be installed, this is a free, open source cross-platform
solution to convert video. It has to be downloaded and installed separately.

Further, Python 3.5 or higher has to be installed as well.


Installation
-------------

This package is available from `pypi <https://pypi.org/project/tesla-dashcam/>`__. Installing it from there will ensure all
other package requirements (except ffmpeg) are installed as well.

Install from pypi is done through:

.. code:: bash

    pip install tesla_dashcam



Usage
-----

.. code:: bash

    tesla_dashcam - Tesla DashCam Creator

    usage:  [-h] --source SOURCE --output OUTPUT
        [--layout {WIDESCREEN,FULLSCREEN}]
        [--quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}]
        [--compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
        [--encoding {x264,x265}] [--timestamp] [--no-timestamp]
        [--ffmpeg FFMPEG] [--font FONT]

    tesla_dashcam - Tesla DashCam Creator

    required arguments:
      --source SOURCE       Folder containing the saved camera files (default:
                            None)

      --output OUTPUT       Path/Filename for the new movie file. (default: None)

    optional arguments:

      -h, --help            show this help message and exit

      --layout {WIDESCREEN,FULLSCREEN}
                            Layout of the video. Widescreen puts video of all 3
                            cameras next to each other. Fullscreen puts the front
                            camera on top in middle and side cameras below it next
                            to each other (default: WIDESCREEN)

      --quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}
                            Define the quality setting for the video, higher
                            quality means bigger file size but might not be
                            noticeable. (default: LOWER)

      --compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                            Speed to optimize video. Faster speed results in a
                            bigger file. This does not impact the quality of the
                            video, just how much time is used to compress it.
                            (default: medium)

      --encoding {x264,x265}
                            Encoding to use. x264 is can be viewed on more devices
                            but results in bigger file. x265 is newer encoding
                            standard (default: x264)

      --timestamp           Include timestamp in video (default)
      --no-timestamp        Do not include timestamp in video

      --ffmpeg FFMPEG       Path and filename for ffmpeg. Specify if ffmpeg is not
                            within path. (default: ffmpeg)

      --font FONT           Fully qualified filename (.ttf) to the font to be
                            chosen for timestamp. (default:
                            /Library/Fonts/Arial.ttf)


layout:
    WIDESCREEN: Resolution: 1920x480
        [Left Camera][Front Camera][Right Camera]

    FULLSCREEN: Resolution: 1280x960
               [Front Camera]

        [Left Camera][Right Camera]



Release Notes
-------------

0.1.1. Initial Release


TODO
----

* Option to specify resolutions as an argument
* Option for end-user layout
* Use create time in clips to synchronize
