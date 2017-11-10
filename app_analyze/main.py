# -*- coding: utf-8 -*-
#
#    Copyright (C) 2017  https://github.com/tbl42
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import json
import time
import redis
import django
import socket
import os.path
import logging
import datetime
import threading

from libyams.utils import get_conf
from django.core.management import execute_from_command_line

# bootstrap ORM
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "libyams.settings")
django.setup()

from libyams.orm.models import TickerData, Indicator

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()


#
# worker thread for analysis
#
class WorkerThread(threading.Thread):
    def __init__(self, redis_con):
        threading.Thread.__init__(self)
        self.redis_con = redis_con
        self.redis_pubsub = redis_con.pubsub()
        self.runner = True

    def run(self):
        global CONFIG
        global DB

        self.redis_pubsub.subscribe(CONFIG["general"]["redis"]["chans"]["analyzer"])

        while self.runner:
            msg = self.redis_pubsub.get_message()

            # logger.debug(msg)

            if isinstance(msg, dict) and msg['type'] == 'message':
                if msg['channel'] == CONFIG["general"]["redis"]["chans"]["analyzer"]:
                    itm = json.loads(msg['data'])['item_data']

                    if "xchg" not in itm.keys() or "pair" not in itm.keys() or "tick" not in itm.keys() or "data" not in itm.keys():
                        logger.debug("data in wrong format, aborting...")
                        continue

                    logger.debug(itm)

                    if not CONFIG["general"]["production"]:
                        self.runner = False

            time.sleep(.5)


#
# MAiN
#
if __name__ == "__main__":

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['general']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # start
    logger.debug("startup redis connection")
    rcon = redis.StrictRedis(host=CONFIG["general"]["redis"]["host"], port=CONFIG["general"]["redis"]["port"], db=0)

    logger.info("start WorkerThread()")
    wt = WorkerThread(rcon)
    wt.start()
    time.sleep(.5)
