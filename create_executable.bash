#!/bin/bash

 pyinstaller --clean \
	--distpath bundles/MacOS/tesla_dashcam \
	--workpath build/MacOS \
	--onefile \
	--osx-bundle-identifier com.ehendrix23.tesla_dashcam \
	--icon tesla_dashcam/tesla_dashcam.ico \
	--add-data="tesla_dashcam/tesla_dashcam.ico:." \
	--add-binary="bundles/MacOS/ffmpeg:." \
	--exclude-module win10toast \
	tesla_dashcam/tesla_dashcam.py
#	--windowed
# pyinstaller  --clean \
#	--distpath tesla_dashcam \
#	--workpath ~/Documents_local/GitHub/tesla_dashcam/build/MacOS \
#	--noconfirm \
#	bundles/MacOS/tesla_dashcam.spec

# codesign -s "com.ehendrix23.tesla_dashcam" bundles/MacOS/tesla_dashcam/tesla_dashcam.app

cd $OLDPWD