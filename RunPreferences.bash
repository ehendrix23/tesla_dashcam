#!/bin/bash

Command="python /Users/ehendrix/Documents_local/GitHub/tesla_dashcam/tesla_dashcam/tesla_dashcam.py"
# InputFolder="/Volumes/TeslaCam/TeslaCam/SavedClips"
InputFolder="/Volumes/TeslaCam/TeslaCam/SentryClips/2020-09-19_*"
OutputFolder="/Volumes/SD Card"
PreferenceFolder="/Users/ehendrix/Documents_local/GitHub/tesla_dashcam/Preference_Files"

for preferencefile in ${PreferenceFolder}/*; do
	filename="${preferencefile##*/}"
	folder=${filename%%.*}
	echo "Using Preference File ${filename}"
	if [ ! -d "${OutputFolder}/${folder}" ]; then
		mkdir "${OutputFolder}/${folder}"
	fi
	${Command} "${InputFolder}" --loglevel DEBUG --output "${OutputFolder}/${folder}" @${preferencefile}
	exit
done

