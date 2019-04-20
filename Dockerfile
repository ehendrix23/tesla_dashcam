FROM python:3

RUN apt-get update && apt-get install -y ffmpeg && apt-get autoremove && apt-get clean

ARG VERSION=v0.1.9b0
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /usr/src/app/tesla_dashcam
RUN git clone https://github.com/ehendrix23/tesla_dashcam.git . && \
    git checkout ${VERSION} && \
    pip install -r requirements.txt

CMD [ "python", "tesla_dashcam/tesla_dashcam.py" ]