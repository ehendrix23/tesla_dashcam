FROM jrottenberg/ffmpeg:4.1-alpine

ENV PYTHONUNBUFFERED=true
WORKDIR /usr/src/app/tesla_dashcam
ENTRYPOINT [ "python", "/usr/src/app/tesla_dashcam/tesla_dashcam.py" ]

RUN apk --no-cache add python3 tzdata ttf-freefont

# ADD requirements.txt  .
# RUN pip install -r requirements.txt

# ADD .  .
