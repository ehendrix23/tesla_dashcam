@echo off
if not exist tesla_dashcam\tesla_dashcam.py (
  echo "Was unable to find tesla_dashcam\tesla_dashcam.py, run this from the folder where tesla_dashcam\tesla_dashcam.py is located within."
  goto :eof
)

if not exist bundles\Windows\ffmpeg.exe (
  echo "Was unable to find tesla_dashcam\bundles\Windows\ffmpeg, ensure tesla_dashcam\bundles\Windows\ffmpeg executable exist."
  goto :eof
)

if not exist tesla_dashcam\tesla_dashcam.ico (
  echo "Was unable to find tesla_dashcam\tesla_dashcam.ico, ensure tesla_dashcam\tesla_dashcam.ico icon file exist."
  goto :eof
)

if not exist bundles\Windows\tesla_dashcam\ (
  mkdir bundles\Windows\tesla_dashcam
)

echo "Installing Python requirements"
pip install -r requirements_create_executable_windows.txt --upgrade

echo "Creating tesla_dashcam executable"
python -m PyInstaller --clean ^
	--distpath bundles\Windows\tesla_dashcam ^
	--workpath build\Windows ^
	--onefile ^
	--icon tesla_dashcam\tesla_dashcam.ico ^
	--add-data="tesla_dashcam\tesla_dashcam.ico;." ^
	--add-binary="bundles\Windows\ffmpeg.exe;." ^
	tesla_dashcam\tesla_dashcam.py

if %ERRORLEVEL% NEQ 0 (
  echo "Failed to create executable."
  goto :eof
)

echo "Creating README.html"
python -m docutils README.rst "bundles\Windows\tesla_dashcam\Tesla_Dashcam - README.html"
if %ERRORLEVEL% NEQ 0 (
  echo "Failed to create README HTML file"
  goto :eof
)

bundles\Windows\tesla_dashcam\tesla_dashcam.exe --version

echo All done.

:eof
