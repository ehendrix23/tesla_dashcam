FROM ubuntu:20.04


ARG DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt install -y ffmpeg python3.8 python3.8-dev python3-pip git fonts-freefont-ttf i965-va-driver-shaders intel-media-va-driver-non-free
RUN git clone -b vaapi-support https://github.com/ehendrix23/tesla_dashcam.git
WORKDIR /tesla_dashcam
RUN ls -al
RUN python3 -m pip install -r requirements.txt

ENV PYTHONUNBUFFERED=true
ENV TZ=America/New_York

ENTRYPOINT [ "python3", "tesla_dashcam/tesla_dashcam.py" ]
