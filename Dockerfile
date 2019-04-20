FROM python:3

RUN apt-get update && apt-get install -y ffmpeg && apt-get autoremove && apt-get clean

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /usr/src/app/tesla_dashcam
ADD . .
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "tesla_dashcam/tesla_dashcam.py" ]