# Docker version for tesla_dashcam

This project is almost completely based off the [ehendrix23/tesla_dashcam project](https://github.com/ehendrix23/tesla_dashcam) and only modifies the DockerFile

The Dockerfile uses the following build images

- [denismakogon/ffmpeg-alpine:4.0-buildstage](https://github.com/denismakogon/ffmpeg-alpine/blob/master/build-stage/Dockerfile)
- [python:3-alpine](https://github.com/docker-library/python/blob/0ecd42b0e0b519259224959b8f9dc64e76d5a73e/3.8/alpine3.10/Dockerfile)

## Basics

To run this as a container you will pass flags on docker run

```docker
    docker run --rm -e TZ=America/New_York magicalyak/tesla_dashcam -h
```

The container uses a default output directory of /root/Videos/Tesla_Dashcam/ you may want to pass this as a mapped volume
So to make a run one could do the following

```docker
    docker run  --name tesla_dashcam \
                -e TZ=America/New_York \
                -v ~/Movies:/root/Videos \
                -v /Volumes/CAM/TeslaCam:/root/Import \
                -rm \
                magicalyak/tesla_dashcam \
                --monitor \
                /root/Import
```

```bash
    --name tesla_dashcam        # names the container (optional)
    -e TZ=America/New_York      # TZ for your locale (needed for timestamps)
    -v ~/Movies:/root/Videos    # export directory (use /root/Videos for mapping)
    -v ~/Import:/root/Import    # you'll need to put in your import directory here
                                # because docker doesn't know your local directories
    --rm                        # This removes the container when done running (you probably want this)
    magicalyak/tesla_dashcam    # this docker container
    --monitor                   # add any options here as you normally would
    /root/Import                # You need to enter the container Import directory here
                                # not your local computer one (it should be entered above)
```

### Docker Container Updating

Docker containers do not update themselves automatically.  If you want to have something run and do this, please take a look at the [watchtower project](https://github.com/containrrr/watchtower)

## ehendrix23 tesla_dashcam overview

Python program that provides an easy method to merge saved Tesla Dashcam footage into a single video.

When saving Tesla Dashcam footage a folder is created on the USB drive and within it multiple MP4 video files are created. Currently the dashcam leverages four (4) cameras (front, rear, left repeater, and right repeater) and will create a
file for each of them. Every minute is stored into a separate file as well. This means that when saving dashcam footage
there is a total of 40 files video files for every 10 minutes. Each block of 10 minutes is put into a folder, thus often
there will be multiple folders.

Using this program, one can combine all of these into 1 video file. The video of the four cameras is merged
into one picture, with the video for all the minutes further put together into one.

By default sub-folders are included when retrieving the video clips. One can, for example, just provide the path to the
respective SavedClips folder (i.e. ```e:\TeslaCam\SavedClips``` for Windows if drive has letter E,
```/Volumes/Tesla/TeslaCam/SavedClips``` on MacOS if drive is mounted on ```/Volumes/Tesla```) and then all folders that were created within the SavedClips folder will be processed. There will be a movie file for each folder.

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

Using the option --monitor_trigger_file one can have it check for existence of a certain file or folder for starting
processing instead of waiting for the disk with the TeslaCam folder to become available. Once available processing will
start, if a trigger file was provided then upon completion of processing the file will then be deleted. If it was a folder
then it will wait for the folder to be removed by something else (or for example link removed) and then wait again for it
to appear again.
If no source folder is provided then folder SavedClips will be processed with assumption it is in the same location as
the trigger file. If source folder is an absolute path (i.e. /Videos/Tesla) then that will be used as source location.
If it is a relative path (i.e. Tesla/MyVideos) then the path will be considered to be relative based on the location
provided for the trigger file.

When using --merge, the name of the resulting video file will be appended with the current timestamp of processing when
--monitor parameter is used, this to ensure that the resulting video file is always unique.
Option --chapter_offset can be provided to offset the chapter markers within the merged video. A negative number would
result in the chapter marker being set not at the start for the folder video but instead be set provided number of
seconds before the end of that video. For example, with 10 minute video for a folder a value of -120 would result
in the chapter markers being set 2 minutes before the end of that video. A positive number will result in chapter marker
being set to provided number of seconds after the start of the video. Value of 300 would result in chapter markers being
set 5 minutes into that folder's video.

If --merge is not provided as an option and there are multiple sub-folders then the filename (if provided in output)
will be ignored. Instead the files will all be placed in the folder identified by the output parameter, one movie file
for each folder. Only exception to this if there was only 1 folder.

By default created videos will be stored within the Tesla_Dashcam folder in the Videos folder (Windows), Movies folder (MacOS), or Videos folder within the user's home directory (Linux).
This can be overriden using the --output parameter.

If no source has been provided then it would be the same as providing parameters --monitor_once and SavedClips as source.
This means that the program will wait until it discovers the USB or SD card with the TeslaCam folder is present and once present it will
start processing all the folders within the SavedClips folder. Once processing of all folders is complete it will then exit.

## ffmpeg information

[ffmpeg](https://www.ffmpeg.org/legal.html) is included within the respective package.
ffmpeg is a separately licensed product under the [GNU Lesser General Public License (LGPL) version 2.1 or later](http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html).
FFmpeg incorporates several optional parts and optimizations that are covered by the GNU General Public License (GPL) version 2 or later. If those parts get used the GPL applies to all of FFmpeg.
For more information on ffmpeg license please see: [ffmpeg legal](https://www.ffmpeg.org/legal.html)

## Notes

The video files for the same minute between the 4 cameras are not always the same length. If there is a difference in
their duration then a black screen will be shown for the camera which video ended before the others (within the minute).
It is thus possible within a video to see a black screen for one of the cameras, and then when that minute has passed
for it to show video again.

The date and time shown within the video comes from the timestamp embedded in the saved videos themselves, not from the
filename. Date and time shown within video is based on PC's timezone.
Tesla embeds the date and time within the video file, and that is what will be displayed comes. This means that the video might
not start exactly at 0 seconds. In the provided video examples one can see that it starts at 16:42:35 and not 16:42:00.

Current caveat however is that the order for concatenating all the videos together is based on filename. (See TODO)

## Usage

```text
    usage: tesla_dashcam.py [-h] [--version] [--exclude_subdirs | --merge]
                            [--start_timestamp START_TIMESTAMP]
                            [--end_timestamp END_TIMESTAMP]
                            [--start_offset START_OFFSET]
                            [--end_offset END_OFFSET]
                            [--chapter_offset CHAPTER_OFFSET] [--output OUTPUT]
                            [--keep-intermediate] [--skip_existing]
                            [--delete_source] [--temp_dir TEMP_DIR]
                            [--no-notification]
                            [--layout {WIDESCREEN,FULLSCREEN,PERSPECTIVE,CROSS,DIAMOND}]
                            [--perspective] [--scale CLIP_SCALE] [--motion_only]
                            [--mirror | --rear] [--swap | --no-swap] [--no-front]
                            [--no-left] [--no-right] [--no-rear]
                            [--slowdown SLOW_DOWN | --speedup SPEED_UP]
                            [--encoding {x264,x265} | --enc ENC] [--no-gpu]
                            [--no-faststart] [--no-timestamp]
                            [--halign {LEFT,CENTER,RIGHT}]
                            [--valign {TOP,MIDDLE,BOTTOM}] [--font FONT]
                            [--fontsize FONTSIZE] [--fontcolor FONTCOLOR]
                            [--quality {LOWEST,LOWER,LOW,MEDIUM,HIGH}]
                            [--compression {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
                            [--ffmpeg FFMPEG] [--monitor] [--monitor_once]
                            [--monitor_trigger MONITOR_TRIGGER]
                            [--check_for_update] [--no-check_for_update]
                            [--include_test]
                            [source [source ...]]

    tesla_dashcam - Tesla DashCam & Sentry Video Creator

    positional arguments:
      source                Folder(s) containing the saved camera files. Filenames
                            can be provided as well to manage individual clips.
                            (default: None)

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program''s version number and exit
      --exclude_subdirs     Do not search sub folders for video files to process.
                            (default: False)
      --merge               Merge the video files from different folders into 1
                            big video file. (default: False)
      --chapter_offset CHAPTER_OFFSET
                            Offset in seconds for chapters in merged video.
                            Negative offset is # of seconds before the end of the
                            subdir video, positive offset if # of seconds after
                            the start of the subdir video. (default: 0)
      --output OUTPUT       Path/Filename for the new movie file. Intermediate files will be stored in same folder.
      --keep-intermediate   Do not remove the intermediate video files that are
                            created (default: False)
      --skip_existing       Skip creating encoded video file if it already exist.
                            Note that only existence is checked, not if layout
                            etc. are the same. (default: False)
      --delete_source       Delete the processed files on the TeslaCam drive.
                            (default: False)
      --temp_dir TEMP_DIR   Path to store temporary files. (default: None)
      --no-notification     Do not create a notification upon completion.
                            (default: True)
      --layout {WIDESCREEN,FULLSCREEN,PERSPECTIVE,CROSS,DIAMOND}
                            Layout of the created video.
                                FULLSCREEN: Front camera center top, side cameras underneath it with rear camera between side camera.
                                WIDESCREEN: Front camera on top with side and rear cameras smaller underneath it.
                                PERSPECTIVE: Similar to FULLSCREEN but then with side cameras in perspective.
                                CROSS: Front camera center top, side cameras underneath, and rear camera center bottom.
                                DIAMOND: Front camera center top, side cameras below front camera left and right of front, and rear camera center bottom.
                             (default: FULLSCREEN)
      --perspective         Show side cameras in perspective. (default: False)
      --scale CLIP_SCALE    Set camera clip scale, scale of 1 is 1280x960 camera clip. Defaults:
                                WIDESCREEN: 1/3 (front 1280x960, others 426x320, video is 1280x960)
                                FULLSCREEN: 1/2 (640x480, video is 1280x960)
                                PERSPECTIVE: 1/4 (320x240, video is 980x380)
                                CROSS: 1/2 (640x480, video is 1280x1440)
                                DIAMOND: 1/2 (640x480, video is 1280x1440)
                             (default: None)
      --motion_only         Fast-forward through video when there is no motion.
                            (default: False)
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
      --no-gpu (MAC)        Use GPU acceleration, only enable if supported by hardware.
                             MAC: All MACs with Haswell CPU or later  support this (Macs after 2013).
                                  See following link as well:
                                     https://en.wikipedia.org/wiki/List_of_Macintosh_models_grouped_by_CPU_type#Haswell
      --gpu (Non-MAC)        Use GPU acceleration, only enable if supported by hardware.
                             MAC: All MACs with Haswell CPU or later  support this (Macs after 2013).
                                  See following link as well:
                                     https://en.wikipedia.org/wiki/List_of_Macintosh_models_grouped_by_CPU_type#Haswell
      --gpu_type (Non-MAC) {nvidia, intel, RPi}
                            Type of graphics card (GPU) in the system. This determines the encoder that will be used.
                            This parameter is mandatory if --gpu is provided.
      --no-faststart        Do not enable flag faststart on the resulting video
                            files. Use this when using a network share and errors
                            occur during encoding. (default: False)
      --ffmpeg FFMPEG       Path and filename for ffmpeg. Specify if ffmpeg is not
                            within path. (default: /Users/ehendrix/Documents_local
                            /GitHub/tesla_dashcam/tesla_dashcam/ffmpeg)

    Timestamp Restriction:
      Restrict video to be between start and/or end timestamps. Timestamp to be
      provided in a ISO-8601format (see https://fits.gsfc.nasa.gov/iso-time.html
      for examples)

      --start_timestamp START_TIMESTAMP
                            Starting timestamp (default: None)
      --end_timestamp END_TIMESTAMP
                            Ending timestamp (default: None)

    Clip offsets:
      Start and/or end offsets

      --start_offset START_OFFSET
                            Starting offset in seconds. (default: None)
      --end_offset END_OFFSET
                            Ending offset in seconds. (default: None)

    Camera Exclusion:
      Exclude one or more cameras:

      --no-front            Exclude front camera from video. (default: False)
      --no-left             Exclude left camera from video. (default: False)
      --no-right            Exclude right camera from video. (default: False)
      --no-rear             Exclude rear camera from video. (default: False)

    Timestamp:
      Options for timestamp:

      --no-timestamp        Include timestamp in video (default: False)
      --halign {LEFT,CENTER,RIGHT}
                            Horizontal alignment for timestamp (default: None)
      --valign {TOP,MIDDLE,BOTTOM}
                            Vertical Alignment for timestamp (default: None)
      --font FONT           Fully qualified filename (.ttf) to the font to be
                            chosen for timestamp. (default:
                            /Library/Fonts/Arial.ttf)
      --fontsize FONTSIZE   Font size for timestamp. Default is scaled based on
                            video scaling. (default: None)
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
      --monitor_trigger MONITOR_TRIGGER
                            Trigger file to look for instead of waiting for drive
                            to be attached. Once file is discovered then
                            processing will start, file will be deleted when
                            processing has been completed. If source is not
                            provided then folder where file is located will be
                            used as source. (default: None)

    Update Check:
      Check for updates

      --check_for_update    Check for updates, do not do anything else. (default:
                            False)
      --no-check_for_update
                            A check for new updates is performed every time. With
                            this parameter that can be disabled (default: False)
      --include_test        Include test (beta) releases when checking for
                            updates. (default: False)
```

## Layout

### `FULLSCREEN:` Resolution: 1920x960

```text
    +---------------+----------------+----------------+
    |               | Front Camera   |                |
    +---------------+----------------+----------------+
    | Left Camera   |  Rear Camera   |  Right Camera  |
    +---------------+----------------+----------------+
```

<iframe width="560" height="315" src="https://www.youtube.com/embed/P5k9PXPGKWQ" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

### `PERSPECTIVE:` Resolution: 1944x1204

```text
    +---------------+----------------+---------------+
    |               | Front Camera   |               |
    |               |                |               |
    +---------------+----------------+---------------+
    | Diagonal Left | Rear Camera    | Diagonal Right|
    | Camera        |                | Camera        |
    +---------------+----------------+---------------+
```

<iframe width="560" height="315" src="https://www.youtube.com/embed/fTUZQ-Ej5AY" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

### `WIDESCREEN:` Resolution: 1920x1920

```text
    +---------------+----------------+----------------+
    |                 Front Camera                    |
    +---------------+----------------+----------------+
    | Left Camera   |  Rear Camera   |  Right Camera  |
    +---------------+----------------+----------------+
```

<iframe width="560" height="315" src="https://www.youtube.com/embed/nPleIhVxyhQ" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

### `CROSS:` Resolution: 1280x1440

```text
    +---------------+----------------+----------------+
    |               | Front Camera   |                |
    +---------------+----------------+----------------+
    |     Left Camera      |       Right Camera       |
    +---------------+----------------+----------------+
    |               | Rear Camera    |                |
    +---------------+----------------+----------------+
```

### `DIAMOND:` Resolution: 1920x976

```text

    +---------------+----------------+----------------+
    |               |  Front Camera  |                |
    +---------------+                +----------------+
    |   Left Camera |----------------| Right Camera   |
    +               +  Rear Camera   +                +
    |---------------|                |----------------|
    +---------------+----------------+----------------+
```

### Examples

#### To show help

```docker
    docker run --rm -e TZ=America/New_York magicalyak/tesla_dashcam -h
```

#### Using defaults

- Mac:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $(pwd):/root/Videos \
        -v /Users/$USER/Desktop/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        /root/Import
    ```

- Linux:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $(pwd):/root/Videos \
        -v $HOME/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        /root/Import
    ```

#### Using defaults but not knowing what to provide for source path. Goal to only process the SavedClips and only do this once. Store the resulting video files in ```/Users/me/Desktop/Tesla``` (MacOS). Delete the files from the USB (or SD) when processed

- Mac:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v ./SavedClips:/root/Import \
        magicalyak/tesla_dashcam \
        --monitor_once --delete_source \
        /root/Import
    ```

- Linux:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v ./SavedClips:/root/Import \
        magicalyak/tesla_dashcam \
        --monitor_once --delete_source \
        /root/Import
    ```

#### Specify video file and location

>Note the output is split between the mapped local directory and the name of the file in the --output option

- Mac:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $HOME/Desktop/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --output /root/Videos/My_Video_trip.mp4 \
        /root/Import
    ```

- Linux:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $HOME/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --output /root/Videos/My_Video_trip.mp4 \
        /root/Import
    ```

#### Without timestamp

- Mac:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $HOME/Desktop/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --no-timestamp \
        /root/Import
    ```

- Linux:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $HOME/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --no-timestamp \
        /root/Import
    ```

#### Put timestamp center top in yellowgreen

- Mac:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $HOME/Desktop/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --fontcolor yellowgreen@0.9 \
        -halign CENTER \
        -valign TOP \
        /root/Import
    ```

- Linux:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $HOME/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --fontcolor yellowgreen@0.9 \
        -halign CENTER \
        -valign TOP \
        /root/Import
    ```

#### Layout so front is shown top middle with side cameras below it and font size of 24 (FULLSCREEN)

- Mac:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $HOME/Desktop/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --layout FULLSCREEN \
        --fontsize 24 \
        /root/Import
    ```

- Linux:

    ```docker
    docker run --rm \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $HOME/Tesla/2019-02-27_14-02-03:/root/Import \
        magicalyak/tesla_dashcam \
        --layout FULLSCREEN \
        --fontsize 24 \
        /root/Import
    ```

#### Enable monitoring for the Tesla Dashcam USB (or SD) to be inserted and then process all the files (both RecentClips and SavedClips)

>Increase speed of resulting videos tenfold and store all videos in folder specified by output.
>Delete the source files afterwards:

- Mac:

    ```docker
    docker run -d --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $(pwd):/root/Import \
        magicalyak/tesla_dashcam \
        --monitor \
        /root/Import
    ```

- Linux:

    ```docker
    docker run -d --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $(pwd):/root/Import \
        magicalyak/tesla_dashcam \
        --monitor \
        /root/Import
    ```

#### Enable one-time monitoring for the Tesla Dashcam USB (or SD) to be inserted and then process all the files from SavedClips

> Note that for source we provide the folder name (SavedClips), the complete path will be created by the program.
Slowdown speed of resulting videos to half, show left/right cameras as if looking backwards, store all videos in folder specified by output.
> Also create a movie file that has them all merged together.

- Mac:

    ```docker
    docker run -d --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $(pwd)/SavedClips:/root/Import \
        magicalyak/tesla_dashcam \
        --slowdown 2 \
        --rear \
        --merge \
        --monitor_once \
        /root/Import
    ```

- Linux:

    ```docker
    docker run -d --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $(pwd)/SavedClips:/root/Import \
        magicalyak/tesla_dashcam \
        --slowdown 2 \
        --rear \
        --merge \
        --monitor_once \
        /root/Import
    ```

#### Enable monitoring using a trigger file (or folder) to start processing all the files from SavedClips

> Note that for source we provide the folder name (SavedClips), the complete path will be created by the program using the
path of the trigger file (if it is a file) or folder. Videos are stored in folder specified by --output. Videos from all
the folders are then merged into 1 folder with name TeslaDashcam followed by timestamp of processing (timestamp is
added automatically). Chapter offset is set to be 2 minutes (120 seconds) before the end of the respective folder clips.

- Mac:

    ```docker
    docker run -d --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $(pwd)/SavedClips:/root/Import \
        -v $(pwd)/TeslaCam/start_processing.txt:/root/Trigger/start_processing.txt \
        magicalyak/tesla_dashcam \
        --merge \
        --chapter_offset -120 \
        --monitor \
        --monitor_trigger /root/Trigger/start_processing.txt \
        /root/Import
    ```

- Linux:

    ```docker
    docker run -d --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $(pwd)/SavedClips:/root/Import \
        -v $(pwd)/TeslaCam/start_processing.txt:/root/Trigger/start_processing.txt \
        magicalyak/tesla_dashcam \
        --merge \
        --chapter_offset -120 \
        --monitor \
        --monitor_trigger /root/Trigger/start_processing.txt \
        /root/Import
    ```

### Start and End Timestamps

By providing either (or both) a start timestamp (```--start_timestamp```) and/or a end timestamp (```--end_timestamp```) one can restrict what is being processed and thus what is being output in the video files based on date/time.

The provided timestamps do not have to match a specific timestamp
of a folder or even of a clip. If the provided timestamp falls within a video clip then the portion of the clip that falls outside of the timestamp(s)
will be skipped.

The format for the timestamp is any valid ISO-8601 format. For example:

```text
2019 to process restrict video to year 2019.
2019-09 for September, 2019.
2019-09-10 or 20190910 for 10th of September, 2019
2019-W37 (or 2019W37) for week 37 in 2019
2019-W37-2 (or 2019W372) for Tuesday (day 2) of Week 37 in 2019
2019-253 (or 2019253) for day 253 in 2019 (which is 10th of September, 2019)
```

To identify the time, one can use ```hh```, ```hh:mm```, or ```hh:mm:ss```.
If providing both a date and a time then these are seperated using the letter T:
```2019-09-10T11:15:10``` for 11:15AM on the 10th of September, 2019.

By default the timezone will be the local timezone. For UTC time add the letter Z to the time: ```2019-09-10T11:15:10Z``` for 11:15AM on the 10th of September, 2019 UTC time.
One can also use +hh:mm, +hhmm, +hh, -hh:mm, -hhmm, -hh to use a different timezone. ```2019-09-10T11:15:10-0500``` is for 11:15AM on the 10th of September, 2019 EST.

For further guidance also see: [iso-time](https://www.cl.cam.ac.uk/~mgk25/iso-time.html)

### Start and End Offsets

Using the parameters ```--start_offset``` and ```--end_offset``` one can set at which point the processing of the clips within the folder should start. The value provided is in seconds.
For example, to skip the 1st 5 minutes of each event (an event being the collection of video files within 1 folder) one can provide ```--start_offset 300```.
Similar, to skip the last 30 seconds of an event one can use ```--end_offset 30```.
The offsets are done for each folder (event) independently. Thus if processing 8 folders and a ```--start_offset 420``` then 8 files will be
created and each will be about 3 minutes long (as each folder normally has 10 minutes worth of video). If using ```--merge``` then the resulting merged video files will be 24 minutes long.

The offsets are calculated before speed-up or slow-down of the video. Hence using ```--start_offset 420 --speed_up 2``` would still result in the offset being at 7 minutes.

## Argument (Parameter) file

It is also possible to supply a text file with all the respective arguments (parameters) instead of having to enter them each time on the command line.

Arguments within the text file can all be on one (1) line, on separate lines, or a combination thereof.

Having a text file (i.e. my_preference.txt) with the following contents:

```bash
    --speedup 10 --rear
    --merge --output /home/me/Tesla
    --monitor_once SavedClips
```

And then executing tesla_dashcam as follows:

- Mac:

    ```docker
    docker run --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Desktop/Tesla:/root/Videos \
        -v $(pwd)/SavedClips:/root/Import \
        -v $(pwd)/my_preference.txt:/root/my_preference.txt \
        magicalyak/tesla_dashcam \
        @/root/mypreference.txt \
        /root/Import
    ```

- Linux:

    ```docker
    docker run --rm \
        --name tesla_dashcam \
        -e TZ=America/New_York \
        -v $HOME/Tesla:/root/Videos \
        -v $(pwd)/SavedClips:/root/Import \
        -v $(pwd)/my_preference.txt:/root/my_preference.txt \
        magicalyak/tesla_dashcam \
        @/root/mypreference.txt \
        /root/Import
    ```

Would result in the same as if those parameters were provided on the command itself. One can also combine a parameter file with parameters on the command line.

Preference is given to what occurs first. For example, if providing the following arguments:

```bash
    --speedup 2 @my_preference.txt
```

Then the clips will only be sped up two-fold instead of 10-fold as ```--speedup 2``` occurs before ```--speedup 10``` from the parameter file.
But with:

```bash
    @my_preference.txt --speedup 2
```

the clips will be sped up ten-fold.

## Support

There is no official support nor should there be any expectation for support to be provided. As per license this is
provided As-Is.

However, any issues or requests can be reported on [ehendrix23 github issues](https://github.com/ehendrix23/tesla_dashcam/issues) and
I will do my best (time permitting) to provide support.

For Docker issues you can report them on the magicalyak [magicalyak github issues](https://github.com/magicalyak/tesla_dashcam/issues)

## Licensing

This project is under the Apache 2 license but many components used have their own licensing.

- [FFMPEG_VERSION](http://ffmpeg.org/releases/): [GNU Lesser General Public License (LGPL) version 2.1](https://ffmpeg.org/legal.html)
- [OGG_VERSION](https://xiph.org/downloads/): [BSD-style license](https://git.xiph.org/?p=mirrors/ogg.git;a=blob_plain;f=COPYING;hb=HEAD)
- [OPENCOREAMR_VERSION](https://sourceforge.net/projects/opencore-amr/files/opencore-amr/): [Apache License](https://sourceforge.net/p/opencore-amr/code/ci/master/tree/LICENSE)
- [VORBIS_VERSION](https://xiph.org/downloads/): [BSD-style license](https://git.xiph.org/?p=mirrors/vorbis.git;a=blob_plain;f=COPYING;hb=HEAD)
- [THEORA_VERSION](https://xiph.org/downloads/): [BSD-style license](https://git.xiph.org/?p=mirrors/theora.git;a=blob_plain;f=COPYING;hb=HEAD)
- [LAME_VERSION](http://lame.sourceforge.net/download.php): [GNU Lesser General Public License (LGPL) version 2.1](http://lame.cvs.sourceforge.net/viewvc/lame/lame/LICENSE?revision=1.9)
- [OPUS_VERSION](https://www.opus-codec.org/downloads/): [BSD-style license](https://www.opus-codec.org/license/)
- [VPX_VERSION](https://github.com/webmproject/libvpx/releases): [BSD-style license](https://github.com/webmproject/libvpx/blob/master/LICENSE)
- [WEBP_VERSION](https://storage.googleapis.com/downloads.webmproject.org/releases/webp/index.html): [BSD-style license](https://github.com/webmproject/libvpx/blob/master/LICENSE)
- [XVID_VERSION](https://labs.xvid.com/source/): [GNU General Public Licence (GPL) version 2](http://websvn.xvid.org/cvs/viewvc.cgi/trunk/xvidcore/LICENSE?revision=851)
- [FDKAAC_VERSION](https://github.com/mstorsjo/fdk-aac/releases): [Liberal but not a license of patented technologies](https://github.com/mstorsjo/fdk-aac/blob/master/NOTICE)
- [FREETYPE_VERSION](http://download.savannah.gnu.org/releases/freetype/): [GNU General Public License (GPL) version 2](https://www.freetype.org/license.html)
- [LIBVIDSTAB_VERSION](https://github.com/georgmartius/vid.stab/releases): [GNU General Public License (GPL) version 2](https://github.com/georgmartius/vid.stab/blob/master/LICENSE)
- [LIBFRIDIBI_VERSION](https://www.fribidi.org/): [GNU General Public License (GPL) version 2](https://cgit.freedesktop.org/fribidi/fribidi/plain/COPYING)
- [X264_VERSION](http://www.videolan.org/developers/x264.html): [GNU General Public License (GPL) version 2](https://git.videolan.org/?p=x264.git;a=blob_plain;f=COPYING;hb=HEAD)
- [X265_VERSION](https://bitbucket.org/multicoreware/x265/downloads/):[GNU General Public License (GPL) version 2](https://bitbucket.org/multicoreware/x265/raw/f8ae7afc1f61ed0db3b2f23f5d581706fe6ed677/COPYING)

## Release Notes

- 0.1.4:
  - Initial Release
- 0.1.5:
  - Fixed: font issue on Windows
- 0.1.6:
  - Changed: Output folder is now optional
  - Changed: Source is positional argument (in preparation for self-contained executable and drag&drop)
- 0.1.7:
  - New: Added perspective layout (thanks to [lairdb](https://model3ownersclub.com/members/lairdb.16314/) from [model3ownersclub](https://model3ownersclub.com>) forums to provide this layout).
  - New: Added font size option to set the font size for timestamp
  - New: Added font color option to set the font color for timestamp
  - New: Added halign option to horizontally align timestamp (left, center, right)
  - New: Added valign option to vertically align timestamp (top, middle, bottom)
  - Changed: Perspective is now default layout.
- 0.1.8:
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
- 0.1.9:
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
  - New: Options --front_scale, --rear_scale, --left_scale, and --right_scale to set the scale of each clip individually (value of 1 is 1280x960 for the clip)
  - New: Option --swap_frontrear to swap front&rear cameras in output.
  - New: Option --background to specify background color (default is black).
  - New: Option --fps to set the frame rate for resulting video. Default is set to 24 (Tesla records at about 33 fps). `Issue #85 <https://github.com/ehendrix23/tesla_dashcam/issues/85>`_
  - New: Parameter file (provided using @) can now include comments (specify using #)
  - New: Option --loglevel to allow for debug information to be printed.
  - Changed: --speedup and --slowdown now accepts a float allowing for example to speed video up by 1.5
  - Changed: Option scale (and clip scale options) also accept fixed resolution (i.e. 640x480) for the clip.
  - Changed: View of rear camera will be mirrored as well if side cameras are shown as mirror
  - Changed: For all layouts default is to show mirror for rear&side if front camera is shown, otherwise show as rear viewing.
  - Changed: Swap left&right cameras when showing rear&side as rear viewing, and not to swap them when showing rear&side as mirror view.
  - Changed: Re-organized help (-h) for all parameters by grouping them.
  - Changed: Added message to install fonts using apt-get install ttf-freefont on Linux if font file is not found.
  - Changed: Only execute if we're main allowing to be imported into other scripts. `Issue #94 <https://github.com/ehendrix23/tesla_dashcam/issues/94>`_
  - Fixed: Providing paths with spaces did not work in parameter files even although it worked from command line. `Issue #89 <https://github.com/ehendrix23/tesla_dashcam/issues/89>`_
  - Fixed: Changed Arial font on MacOS to Arial Unicode (from Arial) as it seems Arial is not available anymore on MacOS 10.15 (Catalina). `Issue #64 <https://github.com/ehendrix23/tesla_dashcam/issues/64>`_
  - Fixed: Incorrect encoder for x265 with Intel GPU hardware encoding - mbaileys
0.1.17:
  - New: Added update checker to determine if there is a newer version, additional arguments to just perform check (--check_for_update), include test releases (--include_test), or disable always checking for updates (--no-check_for_update)

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

