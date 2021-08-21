FROM ehendrix23/ffmpeg-alpine:4.0-buildstage as build-stage
FROM python:3-alpine

COPY --from=build-stage /tmp/fakeroot/bin /usr/local/bin
COPY --from=build-stage /tmp/fakeroot/share /usr/local/share
COPY --from=build-stage /tmp/fakeroot/include /usr/local/include
COPY --from=build-stage /tmp/fakeroot/lib /usr/local/lib

WORKDIR /usr/src/app/tesla_dashcam

RUN apk add --no-cache --update gcc libc-dev linux-headers \
 && apk add --no-cache --update tzdata ttf-freefont libnotify \
 && mkdir /usr/share/fonts/truetype \
 && ln -s /usr/share/fonts/TTF /usr/share/fonts/truetype/freefont

COPY . /usr/src/app/tesla_dashcam
RUN pip install -r requirements.txt

# Enable Logs to show on run
ENV PYTHONUNBUFFERED=true 
# Provide a default timezone
ENV TZ=America/New_York

ENTRYPOINT [ "python3", "tesla_dashcam/tesla_dashcam.py" ]
