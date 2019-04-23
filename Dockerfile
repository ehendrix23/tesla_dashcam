FROM python:3

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y ffmpeg && apt-get autoremove && apt-get clean


WORKDIR /usr/src/app/tesla_dashcam
ADD . .
RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=true

ENTRYPOINT [ "python", "tesla_dashcam/tesla_dashcam.py" ]