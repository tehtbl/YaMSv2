#!/bin/bash
set -e

STAMP="/.grafana-setup-complete"

if [ -f ${STAMP} ]; then
  echo "grafana already configured, nothing to do."
  exit 0
fi

/etc/init.d/grafana-server start

echo 'waiting for grafana boot'
until nc -nv 127.0.0.1 3000 < /dev/null; do sleep 1; done
#until nc -nv localhost 3000 < /dev/null; do sleep 1; done

echo 'config grafana'
sleep 1

# create influxdb datasource
#curl 'http://admin:admin@localhost:3000/api/datasources' \
curl 'http://admin:admin@127.0.0.1:3000/api/datasources' \
    -X POST -H "Content-Type: application/json" \
    --data-binary <<DATASOURCE \
      '{
        "name":"influx",
        "type":"influxdb",
        "url":"http://localhost:8086",
        "access":"proxy",
        "isDefault":true,
        "database":"cryptodb",
        "user":"adm",
        "password":"adm"
      }'
DATASOURCE
echo


/etc/init.d/grafana-server stop

touch ${STAMP}
