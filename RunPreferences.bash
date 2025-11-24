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
	if [ "${OutputFolder}" != "" ]; then
		preference_OutputFolder="${OutputFolder}/${folder}" 
		if [ ! -d "${preference_OutputFolder}" ]; then
			mkdir -p "${preference_OutputFolder}"
		fi
		preference_OutputFolder="--output ""${preference_OutputFolder}""" 

	fi
	echo "Using Preference File ${filename}"
	echo "${Command} ${InputFolders} ${LogLevel} ${preference_OutputFolder} @${preferencefile}  ${StartTimestamp} ${EndTimestamp}"
	${Command} ${InputFolders} ${LogLevel} ${preference_OutputFolder} @${preferencefile} ${StartTimestamp} ${EndTimestamp}
	if [ $? -ne 0 ]; then
		exit 1
	fi
done

