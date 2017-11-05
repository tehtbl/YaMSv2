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

import json
import time
import redis
import django
import os.path
import logging
import datetime

from libyams.utils import get_conf, ticks

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()
CON_REDIS = None
PUBSUB = None

#
# MAiN
#
if __name__ == "__main__":

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['general']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # start
    logger.info("setup redis connection")
    CON_REDIS = redis.StrictRedis(host=CONFIG["general"]["redis"]["host"], port=CONFIG["general"]["redis"]["port"], db=0)
    CON_REDIS.config_set('client-output-buffer-limit', 'normal 0 0 0')
    CON_REDIS.config_set('client-output-buffer-limit', 'slave 0 0 0')
    CON_REDIS.config_set('client-output-buffer-limit', 'pubsub 0 0 0')

    PUBSUB = CON_REDIS.pubsub()
    PUBSUB.subscribe('tracker-data-channel')

    # bootstrap ORM
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    django.setup()

    from libyams.orm.models import TickerData
    CON_REDIS.publish('tracker-db-channel', 'ready')

    # # start up worker thread
    # logger.info("start worker thread")
    # t2 = WorkerThread()
    # t2.start()

    logger.debug("starting storage loop")
    # check if data tracker is ready!!!
    while True:
        msg = PUBSUB.get_message()

        # logger.debug("received msg type:" + str(type(msg)))
        # logger.debug("received msg:" + str(msg))

        if isinstance(msg, dict) and msg['type'] == 'message':
            itm = json.loads(msg['data'])

            if isinstance(itm, dict):
                if "xchg" not in itm.keys() or "pair" not in itm.keys() or "tick" not in itm.keys() or "data" not in itm.keys():
                    logger.debug("data in wrong format, aborting...")
                    continue

                logger.info("valid data (len: %s) from %s for %s at %s" % (len(itm['data']), itm['xchg'], itm['pair'], itm['tick']))

                # logger.debug("itm type:" + str(type(itm)))
                # logger.debug("itm:" + str(itm))

                t1 = time.time()
                to_insert = []
                t_value = map(lambda x: x['tval'], TickerData.objects.filter(xchg=itm['xchg'], pair=itm['pair'], tick=itm['tick']).values('tval'))
                # logger.debug("t_value %s" % t_value)
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

                logger.debug("to insert: %s" % len(to_insert))
                if len(to_insert) > 0:
                    TickerData.objects.bulk_create([
                        TickerData(**i) for i in to_insert
                    ])

                t2 = time.time()
                logger.debug("TIME of saving %s at %s on %s was %s sec" % (itm['pair'], itm['xchg'], itm['tick'], str(t2 - t1)))

                if not CONFIG["general"]["production"]:
                    break

        time.sleep(.01)
        # time.sleep(5)
