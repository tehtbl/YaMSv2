FROM python:2.7

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8

# Default versions
ENV INFLUXDB_VERSION 1.2.0
ENV GRAFANA_VERSION  4.1.1-1484211277

## Database Defaults
#ENV INFLUXDB_GRAFANA_DB datasource
#ENV INFLUXDB_GRAFANA_USER datasource
#ENV INFLUXDB_GRAFANA_PW datasource

ENV LOCAL_APPDIR grafinflux
ENV WORK_APPDIR grafinflux

# Base dependencies
RUN apt-get -y update && \
 apt-get -y --force-yes install \
  apt-utils \
  ca-certificates \
  curl \
  git \
  htop \
  libfontconfig \
  nano \
  net-tools \
  supervisor \
  nginx \
  wget && \
 curl -sL https://deb.nodesource.com/setup_7.x | bash - && \
 apt-get install -y nodejs

# Install InfluxDB
RUN wget https://dl.influxdata.com/influxdb/releases/influxdb_${INFLUXDB_VERSION}_amd64.deb && \
	dpkg -i influxdb_${INFLUXDB_VERSION}_amd64.deb && rm influxdb_${INFLUXDB_VERSION}_amd64.deb

# Install Grafana
RUN wget https://grafanarel.s3.amazonaws.com/builds/grafana_${GRAFANA_VERSION}_amd64.deb && \
	dpkg -i grafana_${GRAFANA_VERSION}_amd64.deb && rm grafana_${GRAFANA_VERSION}_amd64.deb

# influxdb
ADD ./docker/${LOCAL_APPDIR}/influxdb/init.sh /init-influxdb.sh
ADD ./docker/${LOCAL_APPDIR}/influxdb/influxdb.conf /etc/influxdb/influxdb.conf
ADD ./docker/${LOCAL_APPDIR}/influxdb/etc_initd_influxdb /etc/init.d/influxdb
RUN chmod +x /etc/init.d/influxdb
RUN chmod +r /etc/influxdb/influxdb.conf
RUN /bin/bash /init-influxdb.sh

# grafana
ADD ./docker/${LOCAL_APPDIR}/grafana/init.sh /init-grafana.sh
RUN /bin/bash /init-grafana.sh
ADD ./docker/${LOCAL_APPDIR}/grafana/grafana.ini /etc/grafana/grafana.ini

# nginx config
ADD ./docker/${LOCAL_APPDIR}/nginx/nginx.conf /etc/nginx/nginx.conf

# supervisord
ADD ./docker/${LOCAL_APPDIR}/supervisord.conf /etc/supervisord.d/supervisord.conf

## import grafana dashboard
#ADD ./grafana/dash.json /var/lib/grafana/dashboards/dash.json

RUN mkdir -p /var/log/supervisor

# Cleanup
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# expose ports for nginx (grafana)
EXPOSE 80

# expose influxdb data for creating a data volume container
#VOLUME /var/opt/influxdb/

# run
#CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.d/supervisord.conf"]
