FROM jrottenberg/ffmpeg:4.1-alpine

ENV PYTHONUNBUFFERED=true
WORKDIR /usr/src/app/tesla_dashcam
ENTRYPOINT [ "python3", "/usr/src/app/tesla_dashcam/tesla_dashcam.py" ]

RUN sed -i -e 's/v[[:digit:]]\.[[:digit:]]/edge/g' /etc/apk/repositories && \
    apk --no-cache add \
    gcc \
    linux-headers \
    musl-dev \
    python3 \
    python3-dev \
    ttf-freefont \
    tzdata && \
    mkdir -p /usr/share/fonts/truetype/freefont/ &&\
    ln -s /usr/share/fonts/TTF/FreeSans.ttf /usr/share/fonts/truetype/freefont/FreeSans.ttf


ADD requirements.txt  .
RUN python3 -m pip install -r requirements.txt

ADD .  .
