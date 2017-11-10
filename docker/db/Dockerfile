# FROM debian:8
FROM postgres:9.6

ENV LOCAL_APPDIR db
ENV WORK_APPDIR db_scripts

RUN apt-get update
RUN apt-get -y install ntpdate redis-tools

RUN sed -ri 's/exec "\$@"/echo "STARTING postgres"/g' /usr/local/bin/docker-entrypoint.sh

#RUN echo 'cat /usr/local/bin/docker-entrypoint.sh' >> /usr/local/bin/docker-entrypoint.sh
#RUN echo 'exec "$@" &' >> /usr/local/bin/docker-entrypoint.sh
#RUN echo 'sleep 5' >> /usr/local/bin/docker-entrypoint.sh
RUN echo '/usr/bin/redis-cli -h redis ping' >> /usr/local/bin/docker-entrypoint.sh
RUN echo 'exec "$@"' >> /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 5432
CMD ["postgres"]