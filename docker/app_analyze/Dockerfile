# FROM debian:8
FROM python:2.7

ENV LOCAL_APPDIR app_analyze
ENV WORK_APPDIR analyzer

RUN apt-get update
RUN apt-get -y install ntpdate build-essential python-dev gcc automake make python-pip git

RUN pip install numpy==1.13.1

RUN mkdir -p /build
COPY docker/${LOCAL_APPDIR}/ta-lib-0.4.0-src.tar.gz /build
RUN cd /build; tar xf ta-lib-0.4.0-src.tar.gz
RUN cd /build/ta-lib; ./configure --prefix=/usr; make; make install
ENV LD_LIBRARY_PATH /usr/local/lib

ADD ${LOCAL_APPDIR}/reqs.txt /tmp/reqs.txt
RUN pip install --no-cache-dir -r /tmp/reqs.txt

RUN mkdir -p /libyams
COPY libyams /libyams
RUN pip install --no-cache-dir -e /libyams

RUN mkdir -p /${WORK_APPDIR}
WORKDIR /${WORK_APPDIR}

COPY config.yml /${WORK_APPDIR}
COPY docker/${LOCAL_APPDIR}/start.sh /${WORK_APPDIR}/start.sh
RUN chmod +x /${WORK_APPDIR}/start.sh

COPY ${LOCAL_APPDIR} /${WORK_APPDIR}
