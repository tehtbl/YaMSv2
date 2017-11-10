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

from libyams.orm.models import TickerData

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()
DB = {
    'accessible': False,
    'initialized': False
}


#
# checks if db is available
#
def check_db():
    global CONFIG

    try:
        s = socket.create_connection((CONFIG["general"]["database"]["host"], CONFIG["general"]["database"]["port"]), 5)
        s.close()
        return True
    except Exception:
        return False


#
# save data to database
#
def save_to_db(itm):
    # logger.debug("itm type:" + str(type(itm)))
    # logger.debug("itm:" + str(itm))

    t1 = time.time()
    to_insert = []
    t_value = map(lambda x: x['tval'], TickerData.objects.filter(xchg=itm['xchg'], pair=itm['pair'], tick=itm['tick']).values('tval'))

    for d in itm['data']:
        tval = datetime.datetime.strptime(d['tval'], '%Y-%m-%dT%H:%M:%S')
        # logger.debug(tval)
        if tval not in t_value:
            to_insert.append({
                'xchg': itm['xchg'],
                'pair': itm['pair'],
                'tick': itm['tick'],

                'tval': d['tval'],

                'open': d['open'],
                'high': d['high'],
                'low': d['low'],
                'close': d['close']
            })

    logger.info("valid data (%s|%s) from %s for %s at %s" % (len(itm['data']), len(to_insert), itm['xchg'], itm['pair'], itm['tick']))

    if len(to_insert) > 0:
        TickerData.objects.bulk_create([
            TickerData(**i) for i in to_insert
        ])
    # TODO ?!
    # else:
    #     CON_REDIS.publish('tracker-recv-pair', json.dumps({
    #         'xchg': itm['xchg'],
    #         'pair': itm['pair'],
    #         'tick': itm['tick'],
    #     }))

    t2 = time.time()
    logger.debug("TIME of saving %s at %s on %s was %s sec" % (itm['pair'], itm['xchg'], itm['tick'], str(t2 - t1)))

    return


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

        self.redis_pubsub.subscribe(CONFIG["general"]["redis"]["chans"]["db_heartbeat_ctrl"],
                                    CONFIG["general"]["redis"]["chans"]["data"])

        while self.runner:
            msg = self.redis_pubsub.get_message()

            # logger.debug(msg)

            if not DB['accessible']:
                DB['accessible'] = check_db()

            if DB['accessible'] and not DB['initialized']:
                time.sleep(1)
                execute_from_command_line([sys.argv[0], 'makemigrations'])
                execute_from_command_line([sys.argv[0], 'migrate'])

                DB['initialized'] = True

            if isinstance(msg, dict) and msg['type'] == 'message':
                if msg['channel'] == CONFIG["general"]["redis"]["chans"]["db_heartbeat_ctrl"]:
                    itm = msg['data']

                    logger.debug(itm)

                    if itm == 'db_ready':
                        self.redis_con.publish(CONFIG["general"]["redis"]["chans"]["db_heartbeat"], json.dumps({
                            'state': DB['initialized'],
                            'time': int(time.time())
                        }))

                if msg['channel'] == CONFIG["general"]["redis"]["chans"]["data"]:
                    itm = json.loads(msg['data'])

                    if "xchg" not in itm.keys() or "pair" not in itm.keys() or "tick" not in itm.keys() or "data" not in itm.keys():
                        logger.debug("data in wrong format, aborting...")
                        continue

                    save_to_db(itm)
                    itm['data'] = [] # remove data as we get them from db directly

                    self.redis_con.publish(CONFIG["general"]["redis"]["chans"]["analyzer"], json.dumps({
                        'item_data': itm,
                        'time': int(time.time())
                    }))

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
    rcon.config_set('client-output-buffer-limit', 'normal 0 0 0')
    rcon.config_set('client-output-buffer-limit', 'slave 0 0 0')
    rcon.config_set('client-output-buffer-limit', 'pubsub 0 0 0')

    logger.info("start WorkerThread()")
    wt = WorkerThread(rcon)
    wt.start()
    time.sleep(.5)
