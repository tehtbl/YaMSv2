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
import Queue
import random
import django
import os.path
import logging
import threading

from libyams.utils import get_conf, ticks

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()
CON_REDIS = None
PUBSUB = None

# queue_save = Queue.Queue()
thrds_save = []


#
# thread for saving data to database
#
class SaveTickerData(threading.Thread):
    def __init__(self, market, tick, data):
        threading.Thread.__init__(self)
        self.market = market
        self.tick = tick
        self.data = data

    def doit(self):
        logger.info("saving %s at %s on %s" % (self.market.pair, self.market.exchange, self.tick))

        if self.tick not in ticks.keys():
            raise RuntimeError('unknown tick %s for %s' % (self.tick, self.market.exchange))

        counter = 0
        max_tries = 5
        max_wait = random.sample(xrange(15), 1)[0]

        # t1 = time.time()
        td_all = TickerData.objects.filter(market=self.market, tick_len=self.tick)
        td_count_before = len(td_all)
        # t2 = time.time()
        # logger.debug("TIME (td_count_before) of saving %s at %s on %s was %s sec" % (self.market.pair, self.market.exchange, self.tick, str(t2 - t1)))

        while counter < max_tries:
            to_insert = []
            for d in self.data:
                t = TickerData.objects.filter(market=self.market, tick_len=self.tick, time_val=d['time_val'])

                # logger.debug("d: %s" % d)
                # logger.debug("t: %s" % t)

                if not t.exists():
                    to_insert.append({
                        'market': self.market,
                        'tick_len': self.tick,
                        'time_val': d['time_val'],
                        'open': float(d['open']),
                        'high': float(d['high']),
                        'low': float(d['low']),
                        'close': float(d['close'])
                    })

            # t1 = time.time()
            logger.debug("to insert: %s" % len(to_insert))
            TickerData.objects.bulk_create([
                TickerData(**i) for i in to_insert
            ])
            # t2 = time.time()
            # logger.debug("TIME (save data to db) of processing %s at %s on %s was %s sec" % (self.market.pair, self.market.exchange, self.tick, str(t2 - t1)))

            # check if we got new data, if not try again in 7 seconds
            # t1 = time.time()
            # td_count_after = len(TickerData.objects.filter(market=self.market, tick_len=self.tick))
            # t2 = time.time()
            # logger.debug("TIME (td_count_after) of processing %s at %s on %s was %s sec" % (self.market.pair, self.market.exchange, self.tick, str(t2 - t1)))

            # logger.debug("count before %s" % td_count_before)
            # logger.debug("count after  %s" % td_count_after)

            counter = max_tries + 1

            # if td_count_after > td_count_before:
            #     counter = max_tries
            # else:
            #     logger.debug("AGAIN (wait %d s, counter: %d) processing %s at %s on %s" % (max_wait, counter, self.market.pair, self.market.exchange, self.tick))
            #     counter = counter + 1
            #     time.sleep(max_wait)
            #     # TODO: send request to receiver to get new data

        logger.info("finished saving %s at %s on %s" % (self.market.pair, self.market.exchange, self.tick))
        time.sleep(.5)

    def run(self):
        # >> > total_time = timeit.timeit('[v for v in range(10000)]', number=10000)
        t1 = time.time()
        self.doit()
        t2 = time.time()
        logger.debug("TIME of saving %s at %s on %s was %s sec" % (self.market.pair, self.market.exchange, self.tick, str(t2-t1)))


#
# worker thread for analysis
#
class WorkerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = "-WorkerThread-"

    def run(self):
        global CON_REDIS
        global PUBSUB
        global thrds_save

        logger.debug("starting storage worker thread")
        # check if data tracker is ready!!!
        while True:
            msg = PUBSUB.get_message()

            # logger.debug("received msg type:" + str(type(msg)))
            # logger.debug("received msg:" + str(msg))

            # app_tracker_1 | 2017 - 11 - 05 06:01:28, 168 - __main__ - DEBUG - received msg:{'pattern': None, 'type': 'message', 'channel': 'tracker-data-channel', 'data': "{'pair': u'BTC-1ST', 'tick': '5m', 'data': [{'time_val': u'2017-10-16T12:00:00', 'high': 4.313e-05, 'low': 4.177e-05, 'tick_len': '5m', 'close': 4.301e-05, 'open': 4.178e-05, 'market': u'BTC-1ST'}, {'time_val': u'2017-10-16T12:05:00', 'high': 4.2e-05, 'low': 4.2e-05, 'tick_len': '5m', 'close': 4.2e-05, 'open': 4.2e-05, 'market': u'BTC-1ST'}, {'time_val': u'2017-10-16T12:10:00', 'high': 4.21e-05, 'low': 4.202e-05, 'tick_len': '5m', 'close': 4.202e-05, 'open': 4.21e-05, 'market': u'BTC-1ST'}], 'exchange': 'btrx'}"}
            if isinstance(msg, dict) and msg['type'] == 'message':
                itm = json.loads(msg['data'])

                # logger.debug("type: " + str(type(itm)))
                # logger.debug("data: " + str(itm))

                if isinstance(itm, dict):
                    if "exchange" not in itm.keys() or "pair" not in itm.keys() or "tick" not in itm.keys() or "data" not in itm.keys():
                        logger.debug("data in wrong format, aborting...")
                        continue

                    logger.debug("got valid data (len: %s) from tracker '%s' for '%s'" % (len(itm['data']), itm['exchange'], itm['tick']))

                    # t1 = time.time()
                    m, created = Market.objects.get_or_create(exchange=itm['exchange'], pair=itm['pair'])
                    # to_insert = []
                    # for d in itm['data']:
                    #     t = TickerData.objects.filter(market=m, tick_len=itm['tick'], time_val=d['time_val'])
                    #
                    #     # logger.debug("d: %s" % d)
                    #     # logger.debug("t: %s" % t)
                    #
                    #     if not t.exists():
                    #         to_insert.append({
                    #             'market': m,
                    #             'tick_len': itm['tick'],
                    #             'time_val': d['time_val'],
                    #             'open': float(d['open']),
                    #             'high': float(d['high']),
                    #             'low': float(d['low']),
                    #             'close': float(d['close'])
                    #         })
                    #
                    # # t1 = time.time()
                    # logger.debug("to insert: %s" % len(to_insert))
                    # TickerData.objects.bulk_create([
                    #     TickerData(**i) for i in to_insert
                    # ])
                    # t2 = time.time()
                    # logger.debug("TIME of saving %s at %s on %s was %s sec" % (m.pair, m.exchange, itm['tick'], str(t2 - t1)))

                    if len(thrds_save) >= CONFIG["general"]["limit_threads_save"]:
                        t = thrds_save[0]
                        t.join()
                        thrds_save.remove(t)

                    t = SaveTickerData(m, itm['tick'], itm['data'])
                    thrds_save.append(t)
                    t.start()
                    # t.join()

                    if not CONFIG["general"]["production"]:
                        return

            time.sleep(.01)
            # time.sleep(5)


#
# MAiN
#
if __name__ == "__main__":

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['general']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # start
    # if CONFIG["general"]["production"]:
    logger.info("setup redis connection")
    CON_REDIS = redis.StrictRedis(host=CONFIG["general"]["redis"]["host"], port=CONFIG["general"]["redis"]["port"], db=0)
    # CON_REDIS.config_set(client-output-buffer-limit normal 0 0 0)
    CON_REDIS.config_set('client-output-buffer-limit', 'normal 0 0 0')
    CON_REDIS.config_set('client-output-buffer-limit', 'slave 0 0 0')
    CON_REDIS.config_set('client-output-buffer-limit', 'pubsub 0 0 0')

    CON_REDIS.config_get('client-output-buffer-limit')

    PUBSUB = CON_REDIS.pubsub()
    PUBSUB.subscribe('tracker-data-channel')

    # logger.debug(CON_REDIS)
    # logger.debug(PUBSUB)

    # bootstrap ORM
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    django.setup()
    from libyams.orm.models import Market, TickerData
    CON_REDIS.publish('tracker-db-channel', 'ready')

    # start up worker thread
    logger.info("start worker thread")
    t2 = WorkerThread()
    t2.start()
