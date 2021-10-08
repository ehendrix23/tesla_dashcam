#!/bin/bash

if [ ! -f tesla_dashcam/tesla_dashcam.py ]; then
  echo "Was unable to find tesla_dashcam/tesla_dashcam.py, run this from the folder where tesla_dashcam/tesla_dashcam.py is located within."
  exit 1
fi

if [ ! -f bundles/MacOS/ffmpeg ]; then
  echo "Was unable to find tesla_dashcam/bundles/MacOS/ffmpeg, ensure tesla_dashcam/bundles/MacOS/ffmpeg executable exist."
  exit 1
fi

if [ ! -f tesla_dashcam/tesla_dashcam.ico ]; then
  echo "Was unable to find tesla_dashcam/tesla_dashcam.ico, ensure tesla_dashcam/tesla_dashcam.ico icon file exist."
  exit 1
fi

if [ ! -d bundles/MacOS/tesla_dashcam ]; then
  mkdir bundles/MacOS/tesla_dashcam
fi

echo "Installing Python requirements"
pip install -r requirements_create_executable.txt --upgrade

echo "Creating tesla_dashcam executable"
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

if [ $? -ne 0 ]; then
  echo "Failed to create executable."
  exit 1
fi

echo "Creating README.html"
rst2html.py README.rst bundles/MacOS/tesla_dashcam/Tesla_Dashcam\ -\ README.html
if [ $? -ne 0 ]; then
  echo "Failed to create README.html."
  exit 1
fi

# codesign -s "com.ehendrix23.tesla_dashcam" bundles/MacOS/tesla_dashcam/tesla_dashcam.app
# if [ $? -ne 0 ]; then
#  echo "Failed to sign the app however executable should still function."
#  exit 1
# fi

./bundles/MacOS/tesla_dashcam/tesla_dashcam --version

echo All done.
