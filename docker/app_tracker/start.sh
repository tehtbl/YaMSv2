#!/usr/bin/env bash

if [ -f /tmp/FIRST_START ];
then
    echo "wait for db bootstrap"
    sleep 25
    rm -rf /tmp/FIRST_START
fi

sleep 5

/usr/local/bin/python /tracker/manage.py makemigrations
/usr/local/bin/python /tracker/manage.py migrate
/usr/local/bin/python /tracker/main.py

exit 0