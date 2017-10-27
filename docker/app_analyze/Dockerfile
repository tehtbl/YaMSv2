# FROM debian:8
FROM python:2.7

ENV LOCAL_APPDIR app_analyze
ENV WORK_APPDIR analyzer

RUN apt-get update
RUN apt-get -y install ntpdate

RUN mkdir -p /libyams
COPY libyams /libyams
RUN pip install --no-cache-dir -e /libyams

ADD ${LOCAL_APPDIR}/reqs.txt /tmp/reqs.txt
RUN pip install --no-cache-dir -r /tmp/reqs.txt

RUN mkdir -p /${WORK_APPDIR}
WORKDIR /${WORK_APPDIR}

COPY config.yml /tracker
COPY docker/${LOCAL_APPDIR}/start.sh /${WORK_APPDIR}/start.sh
RUN chmod +x /${WORK_APPDIR}/start.sh

COPY ${LOCAL_APPDIR} /${WORK_APPDIR}