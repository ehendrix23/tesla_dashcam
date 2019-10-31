#!/bin/bash
#title          :teslaarchive.sh
#description    :This script archives tesla_dashcam video from teslausb
#author         :Tom Gamull
#date           :20191024
#version        :1.0    
#usage          :./teslaarchiver
#notes          :       
#bash_version   :3.2.57(1)-release
#============================================================================
# Goal is to run nightly 
# 0) run nightly or test for .archive file and run if it's the next day?
# 1) create directory for date
# 2) convert videos daily to the destination date directory
# 3) merge videos and remove the intermediates
# 4) archive videos in local directory (copy dir to archive sub folder)
# 5) remove archive videos in local directory after 30 days unless file .preserve is present
#============================================================================
shopt -s extglob # Needed for directory except loop command below

destroot="/mnt2/tesla_dashcam"
sourceroot="/mnt2/tesla"

echo "Looping through $sourceroot/ for teslacam video to move"
for dirsource in ${sourceroot}/!(archive|processing)/; do
	if [ -d ${dirsource} ]; then
		sourcedirdate=$(basename $dirsource | cut -d'_' -f1)
		dir_time=$(date -d $sourcedirdate +%s)
		if [ $dir_time -le $(date -d 'now - 1 day' +%s) ] || [ $sourcedirdate == $(date -d 'now - 1 day' +%Y-%m-%d) ]; then
			echo "$dirsource is over 24 hours old"
			destpath="${destroot}/${sourcedirdate}"
			if [ ! -d "$destpath" ]; then
				echo "Creating $destpath"
				mkdir $destpath;
			fi
			processpath="${sourceroot}/processing/${sourcedirdate}"
			if [ ! -d "$processpath" ]; then
				echo "Creating $processpath"
				mkdir $processpath;
			fi
			echo "Moving $disource to processing directory $processpath"
			mv $dirsource $processpath
		fi
	else
		echo "No directories found to process!"
	fi
done

echo "Converting Videos from processing folder with tesla_dashcam container"
for dirprocess in ${sourceroot}/processing/*/; do
	if [ -d ${dirprocess} ]; then
		processdirdate=$(basename $dirprocess)
		docker run --rm \
		-e TZ=America/New_York \
		-v $destroot/$processdirdate:/root/Videos \
		-v $dirprocess:/root/Import \
		magicalyak/tesla_dashcam \
		--motion_only \
		--merge /root/Import \
		--output /root/Videos/$processdirdate.mp4
		echo "Archiving folder in $sourceroot/archive/$processdirdate"
		mv $dirprocess $sourceroot/archive/$processdirdate
		echo "Removing intermediate files in $destroot/$processdirdate"
		for file in ${destroot}/${processdirdate}/*; do
			if [[ $file == *"${processdirdate}T"* ]]; then
				echo "Deleting $file"
				rm -f $file
			fi
		done
	else
		echo "No directories found to convert!"
	fi
done


echo "Removing directories in $sourceroot/archive if over 3 months and .preserve isn't present"
for dirarchive in ${sourceroot}/archive/*/; do
	archivedirdate=$(basename $dirarchive)
	dir_time=$(date -d $archivedirdate +%s)
	if [ $dir_time -le $(date -d 'now - 3 months' +%s) ]; then
		if [ -f "${dirarchive}/.preserve" ]; then
			echo ".preserve file found in $dirarchive! Skipping..."
		else
			echo "Removing $dirarchive since it is over 3 months old"
			rm -rf $dirarchive
		fi
	fi
done