#!/bin/bash

# Small script that will run tesla_dashcam leveraging all the different preferences provided in the Preference_Files folder.

# Folder(s) to scan for clips
InputFolders='/Volumes/TeslaCam/TeslaCam/SentryClips /Volumes/TeslaCam/TeslaCam/SavedClips'

# Folder to store resulting movie files.
OutputFolder='/Volumes/TeslaCam/Movies'

# Start Timestamp
StartTimestamp=""
# StartTimestamp="2020-09-19T13:29:10"

# End Timestamp
EndTimestamp=""
# EndTimestamp="2020-09-19T13:29:30"

# Path to folder containing the preference files
PreferenceFolder="./Preference_Files"


# LogLevel
LogLevel=""
# LogLevel="DEBUG"

if [ -f tesla_dashcam/tesla_dashcam.py ]; then
	Command="tesla_dashcam/tesla_dashcam.py"
else
	Command="tesla_dashcam.py"
fi
Command="python ${Command}"

if [ "${OutputFolder}" != "" ]; then
	if [ ! -d ${OutputFolder} ]; then
		mkdir ${OutputFolder}
	fi
	OutputFolder="--output ""${OutputFolder}""" 
fi

if [ "${StartTimestamp}" != "" ]; then
	StartTimestamp="--start_timestamp ${StartTimestamp}"
fi
if [ "${EndTimestamp}" != "" ]; then
	EndTimestamp="--end_timestamp ${EndTimestamp}"
fi

if [ "${LogLevel}" != "" ]; then
	LogLevel="--loglevel ${LogLevel}"
fi

for preferencefile in ${PreferenceFolder}/*; do
	filename="${preferencefile##*/}"
	folder=${filename%%.*}
	echo "Using Preference File ${filename}"
	echo "${Command} ${InputFolders} ${LogLevel} ${OutputFolder} @${preferencefile}  ${StartTimestamp} ${EndTimestamp}"
	${Command} ${InputFolders} ${LogLevel} ${OutputFolder} @${preferencefile} ${StartTimestamp} ${EndTimestamp}
done

