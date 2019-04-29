FROM python:3

ENV PYTHONUNBUFFERED=true
WORKDIR /usr/src/app/tesla_dashcam
ENTRYPOINT [ "python", "/usr/src/app/tesla_dashcam/tesla_dashcam.py" ]


WORKDIR /usr/src/app/tesla_dashcam
ADD . .
RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=true

ADD .  .
