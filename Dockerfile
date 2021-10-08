FROM linuxserver/ffmpeg as build-stage
FROM python:3-alpine

COPY --from=build-stage /usr/local/bin /usr/local/bin
COPY --from=build-stage /usr/local/share /usr/local/share
COPY --from=build-stage /usr/local/include /usr/local/include
COPY --from=build-stage /usr/local/lib /usr/local/lib

WORKDIR /usr/src/app/tesla_dashcam

RUN apk add --no-cache --update gcc libc-dev linux-headers \
 && apk add --no-cache --update tzdata ttf-freefont libnotify jpeg-dev zlib-dev \
 && mkdir /usr/share/fonts/truetype \
 && ln -s /usr/share/fonts/TTF /usr/share/fonts/truetype/freefont

ENV LIBRARY_PATH=/lib:/usr/lib

COPY . /usr/src/app/tesla_dashcam
RUN pip install -r requirements.txt

# Enable Logs to show on run
ENV PYTHONUNBUFFERED=true 
# Provide a default timezone
ENV TZ=America/New_York

ENTRYPOINT [ "python3", "tesla_dashcam/tesla_dashcam.py" ]