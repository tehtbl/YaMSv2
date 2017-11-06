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
import json
import time
import redis
import django
import os.path
import logging
import datetime

from libyams.utils import get_conf

# bootstrap ORM
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from libyams.orm.models import TickerData

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
    logger.info("startup redis connection")
    CON_REDIS = redis.StrictRedis(host=CONFIG["general"]["redis"]["host"], port=CONFIG["general"]["redis"]["port"], db=0)
    CON_REDIS.config_set('client-output-buffer-limit', 'normal 0 0 0')
    CON_REDIS.config_set('client-output-buffer-limit', 'slave 0 0 0')
    CON_REDIS.config_set('client-output-buffer-limit', 'pubsub 0 0 0')

    CON_REDIS.publish('tracker-db-channel', 'ready')

    PUBSUB = CON_REDIS.pubsub()
    PUBSUB.subscribe('tracker-data-channel')

    logger.info("starting storage loop")
    while True:
        msg = PUBSUB.get_message()

        if isinstance(msg, dict) and msg['type'] == 'message' and msg['channel'] == 'tracker-data-channel':
            itm = json.loads(msg['data'])

            if isinstance(itm, dict):
                if "xchg" not in itm.keys() or "pair" not in itm.keys() or "tick" not in itm.keys() or "data" not in itm.keys():
                    logger.debug("data in wrong format, aborting...")
                    continue

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

                logger.info("valid data (%s|%s) from %s for %s at %s" % (len(itm['data']), len(to_insert), itm['xchg'], itm['pair'], itm['tick']))

                if len(to_insert) > 0:
                    TickerData.objects.bulk_create([
                        TickerData(**i) for i in to_insert
                    ])
                # TODO
                # else:
                #     CON_REDIS.publish('tracker-recv-pair', json.dumps({
                #         'xchg': itm['xchg'],
                #         'pair': itm['pair'],
                #         'tick': itm['tick'],
                #     }))

                t2 = time.time()
                logger.debug("TIME of saving %s at %s on %s was %s sec" % (itm['pair'], itm['xchg'], itm['tick'], str(t2 - t1)))

                if not CONFIG["general"]["production"]:
                    break

        time.sleep(.01)
        # time.sleep(5)
