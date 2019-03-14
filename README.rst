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
solution to convert video. It has to be downloaded and installed separately.

`Python <https://www.python.org>`__ 3.5 or higher is also required.


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

    usage:  [-h] --output OUTPUT
        [--layout {WIDESCREEN,FULLSCREEN}]
        [--quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}]
        [--compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
        [--encoding {x264,x265}] [--timestamp] [--no-timestamp]
        [--ffmpeg FFMPEG] [--font FONT]
        source

    tesla_dashcam - Tesla DashCam Creator

    required arguments:
      source                Folder containing the saved camera files (default:
                            None)

    optional arguments:

      -h, --help            show this help message and exit

      --output OUTPUT       Path/Filename for the new movie file. (default: None)

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
Video example: https://youtu.be/nPleIhVxyhQ

::

    +---------------+----------------+---------------+
    | Left Camera   | Front Camera   | Right Camera  |
    +---------------+----------------+---------------+


FULLSCREEN: Resolution: 1280x960
Video example: https://youtu.be/P5k9PXPGKWQ

::

    +---------------+----------------+
    |           Front Camera         |
    +---------------+----------------+
    | Left Camera   |  Right Camera  |
    +---------------+----------------+



Examples
--------

To show help:

.. code:: bash

    python3 -m tesla_dashcam -h

Using defaults:

* Windows:

.. code:: bash

    python3 -m tesla_dashcam c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 -m tesla_dashcam /Users/me/Desktop/Tesla/2019-02-27_14-02-03

Specify video file and location:

* Windows:

.. code:: bash

    python3 -m tesla_dashcam --output c:\Tesla\My_Video_Trip.mp4 c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 -m tesla_dashcam --output /Users/me/Desktop/Tesla/My_Video_Trip.mp4 /Users/me/Desktop/Tesla/2019-02-27_14-02-03

Without timestamp:

* Windows:

.. code:: bash

    python3 -m tesla_dashcam --no-timestamp c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 -m tesla_dashcam --no-timestamp /Users/me/Desktop/Tesla/2019-02-27_14-02-03


Layout so front is shown top middle with side cameras below it (FULLSCREEN):

* Windows:

.. code:: bash

    python3 -m tesla_dashcam --layout FULLSCREEN c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 -m tesla_dashcam --layout FULLSCREEN /Users/me/Desktop/Tesla/2019-02-27_14-02-03


Specify location of ffmpeg binay (in case ffmpeg is not in path):

* Windows:

.. code:: bash

    python3 -m tesla_dashcam --ffmpeg c:\ffmpeg\ffmpeg.exe c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 -m tesla_dashcam --ffmpeg /Applications/ffmpeg /Users/me/Desktop/Tesla/2019-02-27_14-02-03

Layout of FULLSCREEN with a different font for timestamp and path for ffmpeg:

* Windows: Note how to specify the path, : and \ needs to be escaped by putting a \ in front of them.

.. code:: bash

    python3 -m tesla_dashcam --layout FULLSCREEN --ffmpeg c:\ffmpeg\ffmpeg.exe --font "C\:\\Windows\\Fonts\\Courier New.ttf" c:\Tesla\2019-02-27_14-02-03

* Mac:

.. code:: bash

    python3 -m tesla_dashcam --layout FULLSCREEN --ffmpeg /Applications/ffmpeg --font '/Library/Fonts/Courier New.ttf' /Users/me/Desktop/Tesla/2019-02-27_14-02-03


Support
-------

There is no official support nor should there be any expectation for support to be provided. As per license this is
provided As-Is.
However, any issues or requests can be reported on `GitHub <https://github.com/ehendrix23/tesla_dashcam/issues>`__.


Release Notes
-------------

0.1.4.
    Initial Release
0.1.5
    Fixed font issue on Windows
0.1.6
    Output folder is now optional
    source is positional argument (in preparation for self-contained executable and drag&drop)


TODO
----

* Create self-contained executable for MacOS and Windows
* Support drag&drop of video folder
* Create GUI for options
* Option to specify resolutions as an argument
* Option for end-user layout
* Use timestamp in video to determine order instead of file name
* Use timestamp in video to ensure full synchronization between the 3 cameras
