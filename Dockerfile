FROM jrottenberg/ffmpeg:4.4-alpine312 as build-stage
FROM python:3-alpine

COPY --from=build-stage /usr/local/bin /usr/local/bin
COPY --from=build-stage /usr/local/share /usr/local/share
COPY --from=build-stage /usr/local/include /usr/local/include
COPY --from=build-stage /usr/local/lib /usr/local/lib

ENV LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib

ARG DEBIAN_FRONTEND=noninteractive

RUN apk add --no-cache --update \
    gcc \
    libc-dev \
    linux-headers \
    tzdata \
    ttf-freefont \
    libnotify \
    jpeg-dev \
    zlib-dev \
    openssl-dev \
    # ffmpeg-libs \
 && mkdir /usr/share/fonts/truetype \
 && ln -s /usr/share/fonts/TTF /usr/share/fonts/truetype/freefont

ENV PYTHONUNBUFFERED=true
ENV TZ=America/New_York

ENTRYPOINT [ "python3", "tesla_dashcam/tesla_dashcam.py" ]
