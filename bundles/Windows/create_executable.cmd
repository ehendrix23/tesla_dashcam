pushd z:\tesla_dashcam
pyinstaller --clean ^
	--distpath bundles\Windows\tesla_dashcam ^
	--workpath build\Windows ^
	--onefile ^
	--icon tesla_dashcam\tesla_dashcam.ico ^
	--add-data="tesla_dashcam\tesla_dashcam.ico;." ^
	--add-binary="bundles\Windows\ffmpeg.exe;." ^
	tesla_dashcam\tesla_dashcam.py

popd
