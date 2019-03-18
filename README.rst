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

Binaries
--------

Stand-alone binaries can be retrieved:

- Windows: https://github.com/ehendrix23/tesla_dashcam/dist/tesla_dashcam.exe
- MacOS (OSX): https://github.com/ehendrix23/tesla_dashcam/dist/tesla_dashcam

ffmpeg still has to be downloaded and installed separately.

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

    usage: tesla_dashcam.py [-h] [--output OUTPUT]
                            [--layout {WIDESCREEN,FULLSCREEN,PERSPECTIVE}]
                            [--quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}]
                            [--compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
                            [--encoding {x264,x265}] [--timestamp]
                            [--no-timestamp] [--halign {LEFT,CENTER,RIGHT}]
                            [--valign {TOP,MIDDLE,BOTTOM}] [--font FONT]
                            [--fontsize FONTSIZE] [--fontcolor FONTCOLOR]
                            [--ffmpeg FFMPEG]
                            source

    tesla_dashcam - Tesla DashCam Creator

    positional arguments:
      source                Folder containing the saved camera files

    optional arguments:
      -h, --help            show this help message and exit
      --output OUTPUT       Path/Filename for the new movie file.
      --layout {WIDESCREEN,FULLSCREEN,PERSPECTIVE}
                            Layout of the created video.
                                PERSPECTIVE: Front camera center top, side cameras next to it in perspective.
                                WIDESCREEN: Output from all 3 cameras are next to each other.
                                FULLSCREEN: Front camera center top, side cameras underneath it.
      --quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}
                            Define the quality setting for the video, higher
                            quality means bigger file size but might not be
                            noticeable.
      --compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                            Speed to optimize video. Faster speed results in a
                            bigger file. This does not impact the quality of the
                            video, just how much time is used to compress it.
      --encoding {x264,x265}
                            Encoding to use. x264 can be viewed on more devices
                            but results in bigger file. x265 is newer encoding
                            standard but not all devices support this yet.
      --timestamp           Include timestamp in video
      --no-timestamp        Do not include timestamp in video
      --halign {LEFT,CENTER,RIGHT}
                            Horizontal alignment for timestamp
      --valign {TOP,MIDDLE,BOTTOM}
                            Vertical Alignment for timestamp
      --font FONT           Fully qualified filename (.ttf) to the font to be
                            chosen for timestamp.
      --fontsize FONTSIZE   Font size for timestamp.
      --fontcolor FONTCOLOR
                            Font color for timestamp. Any color is accepted as a color string or RGB value.
                            Some potential values are:
                                white
                                yellowgreen
                                yellowgreen@0.9
                                Red
                                0x2E8B57
                            For more information on this see ffmpeg documentation for color: https://ffmpeg.org/ffmpeg-utils.html#Color
      --ffmpeg FFMPEG       Path and filename for ffmpeg. Specify if ffmpeg is not
                            within path.


Layout:
-------

PERSPECTIVE: Resolution: 980x380
::

    +---------------+----------------+---------------+
    | Diagonal Left | Front Camera   | Diagonal Right|
    | Camera        |                | Camera        |
    +---------------+----------------+---------------+

Video example: https://youtu.be/fTUZQ-Ej5AY


WIDESCREEN: Resolution: 1920x480
::

    +---------------+----------------+---------------+
    | Left Camera   | Front Camera   | Right Camera  |
    +---------------+----------------+---------------+

Video example: https://youtu.be/nPleIhVxyhQ

FULLSCREEN: Resolution: 1280x960
::

    +---------------+----------------+
    |           Front Camera         |
    +---------------+----------------+
    | Left Camera   |  Right Camera  |
    +---------------+----------------+

Video example: https://youtu.be/P5k9PXPGKWQ


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


TODO
----

* Create self-contained executable for MacOS and Windows
* Support drag&drop of video folder
* Create GUI for options
* Option to specify resolutions as an argument
* Option for end-user layout
* Use timestamp in video to determine order instead of file name
* Use timestamp in video to ensure full synchronization between the 3 cameras
