FROM python:3-slim

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
    # FFmpeg with GPU support
    ffmpeg \
    # Application dependencies
    fonts-freefont-ttf \
    libnotify-bin \
    # Build essentials for psutil.
    build-essential \
    python3-dev \    
    # git etc. to get latest pre-release
    git \
    && apt-get remove --purge --auto-remove -y && rm -rf /var/lib/apt/lists/*

ENV LIBRARY_PATH=/lib:/usr/lib

WORKDIR /usr/src/app/tesla_dashcam

# Install tesla_dashcam
RUN pip install --no-cache-dir tesla_dashcam

# Enable Logs to show on run
ENV PYTHONUNBUFFERED=true
# Provide a default timezone
ENV TZ=America/New_York

ENTRYPOINT ["python3", "-m", "tesla_dashcam"]