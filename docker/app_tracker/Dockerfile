# FROM debian:8
FROM python:2.7

ENV LOCAL_APPDIR app_tracker
ENV WORK_APPDIR tracker

RUN apt-get update
RUN apt-get -y install ntpdate

ADD ${LOCAL_APPDIR}/reqs.txt /tmp/reqs.txt
RUN pip install --no-cache-dir -r /tmp/reqs.txt

RUN mkdir -p /libyams
COPY libyams /libyams
RUN pip install --no-cache-dir -e /libyams

RUN mkdir -p /${WORK_APPDIR}
WORKDIR /${WORK_APPDIR}

COPY config.yml /tracker

COPY ${LOCAL_APPDIR} /${WORK_APPDIR}
