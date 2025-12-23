#!/bin/bash

if [ ! -f tesla_dashcam/tesla_dashcam.py ]; then
  echo "Was unable to find tesla_dashcam/tesla_dashcam.py, run this from the folder where tesla_dashcam/tesla_dashcam.py is located within."
  exit 1
fi

if [ ! -f bundles/MacOS/ffmpeg ]; then
  echo "Was unable to find tesla_dashcam/bundles/MacOS/ffmpeg, ensure tesla_dashcam/bundles/MacOS/ffmpeg executable exist."
  exit 1
fi

ICON_ICNS="bundles/MacOS/tesla_dashcam.icns"

if [ ! -f "$ICON_ICNS" ]; then
  echo "Was unable to find $ICON_ICNS, ensure the ICNS icon file exists."
  exit 1
fi

if [ ! -d bundles/MacOS/tesla_dashcam ]; then
  mkdir bundles/MacOS/tesla_dashcam
fi

echo "Installing Python requirements"
pip install -r bundles/MacOS/requirements_create_executable.txt --upgrade

echo "Creating tesla_dashcam executable"
 pyinstaller --clean \
	--distpath bundles/MacOS/tesla_dashcam \
	--workpath build/MacOS \
	--onefile \
	--osx-bundle-identifier com.ehendrix23.tesla_dashcam \
  --icon "$ICON_ICNS" \
	--add-binary="bundles/MacOS/ffmpeg:." \
	--exclude-module win11toast \
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
python3 -m markdown -x extra -x toc -x fenced_code -x tables README.md > README.html
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

echo "Setting executable icon"
python3 - "$ICON_ICNS" "bundles/MacOS/tesla_dashcam/tesla_dashcam" <<'PYTHON'
import sys
import os
from pathlib import Path

icon_path = sys.argv[1]
exe_path = sys.argv[2]

try:
    from AppKit import NSImage, NSWorkspace
    
    # Load the icon
    icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
    if icon is None:
        print(f"Failed to load icon from {icon_path}", file=sys.stderr)
        sys.exit(1)
    
    # Set icon on the executable
    ws = NSWorkspace.sharedWorkspace()
    success = ws.setIcon_forFile_options_(icon, exe_path, 0)
    
    if success:
        print(f"Icon set successfully")
    else:
        print(f"Failed to set icon", file=sys.stderr)
        sys.exit(1)
except ImportError:
    print("AppKit not available; skipping icon setting", file=sys.stderr)
except Exception as e:
    print(f"Error setting icon: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON

if [ $? -ne 0 ]; then
  echo "Warning: Failed to set icon."
fi

echo "Creating disk image"
DMG_STAGING="build/MacOS/dmg_root"
DMG_RW="build/MacOS/Tesla_Dashcam_rw.dmg"
DMG_PATH="bundles/MacOS/Tesla_Dashcam.dmg"
DMG_VOLNAME="Tesla Dashcam"

rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"

# Copy payload into staging
cp bundles/MacOS/tesla_dashcam/tesla_dashcam "$DMG_STAGING"/
cp README.html "$DMG_STAGING"/
cp LICENSE "$DMG_STAGING"/
cp ffmpeg_LICENSE.txt "$DMG_STAGING"/

# Create temporary read-write DMG
rm -f "$DMG_RW"
hdiutil create \
  -fs HFS+ \
  -volname "$DMG_VOLNAME" \
  -srcfolder "$DMG_STAGING" \
  -format UDRW \
  -o "$DMG_RW"

if [ $? -ne 0 ]; then
  echo "Failed to create temporary DMG."
  exit 1
fi

# Mount the temporary DMG, set icon, then unmount
echo "Setting volume icon"
DMG_MOUNT_POINT="/Volumes/$DMG_VOLNAME"
hdiutil attach "$DMG_RW" -nobrowse

python3 - "$ICON_ICNS" "$DMG_MOUNT_POINT" <<'PYTHON'
import sys
import os

icon_path = sys.argv[1]
vol_path = sys.argv[2]

try:
    from AppKit import NSImage, NSWorkspace
    
    # Load the icon
    icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
    if icon is None:
        print(f"Failed to load icon from {icon_path}", file=sys.stderr)
        sys.exit(1)
    
    # Set icon on the volume
    ws = NSWorkspace.sharedWorkspace()
    success = ws.setIcon_forFile_options_(icon, vol_path, 0)
    
    if success:
        print(f"Volume icon set successfully")
    else:
        print(f"Failed to set volume icon", file=sys.stderr)
        sys.exit(1)
except ImportError:
    print("AppKit not available; skipping volume icon setting", file=sys.stderr)
except Exception as e:
    print(f"Error setting volume icon: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON

hdiutil detach "$DMG_MOUNT_POINT"

# Convert to compressed UDZO format
echo "Compressing disk image"
rm -f "$DMG_PATH"
hdiutil convert "$DMG_RW" -format UDZO -o "$DMG_PATH"
if [ $? -ne 0 ]; then
  echo "Failed to compress DMG."
  exit 1
fi
rm -f "$DMG_RW"

echo All done.
