FROM jrottenberg/ffmpeg:7-scratch AS ffmpeg
FROM python:3-slim

COPY --from=ffmpeg /bin/ffmpeg /bin/ffprobe /usr/local/bin/
COPY --from=ffmpeg /lib /lib
COPY --from=ffmpeg /share /share

RUN apt-get update -y \
    && apt-get install -y \
    fonts-freefont-ttf \
    libnotify-bin \
    libva2 \
    libva-drm2 \
    git \
    && apt-get remove --purge --auto-remove -y && rm -rf /var/lib/apt/lists/*

ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /usr/src/app
RUN git clone https://github.com/ehendrix23/tesla_dashcam.git .

WORKDIR /usr/src/app/tesla_dashcam
# COPY . /usr/src/app/tesla_dashcam

RUN pip install -r requirements.txt

# Enable Logs to show on run
ENV PYTHONUNBUFFERED=true
# Provide a default timezone
ENV TZ=America/New_York

ENTRYPOINT [ "python3", "tesla_dashcam/tesla_dashcam.py" ]