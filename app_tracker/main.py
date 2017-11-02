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

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from django.core.management import execute_from_command_line

from libyams.utils import get_conf, ticks

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

CONFIG = get_conf()
# STATUS_RECV = False
CON_REDIS = None

queue_save = Queue.Queue()
thrds_save = []

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTALLED_APPS = [
    'libyams.orm'
]

DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'yamsdb',
        'USER': 'pguser',
        'PASSWORD': 'supersecret',
        'HOST': 'db',
        'PORT': 5432
    }
}

SECRET_KEY = 'NOT NEEDED...'


#
# thread for saving data to database
#
class SaveTickerData(threading.Thread):
    def __init__(self, exchange, pair, tick, data):
        threading.Thread.__init__(self)
        self.exchg = exchange # TODO: muss ein Market model sein!
        self.pair = pair
        self.tick = tick
        self.data = data

    def doit(self):
        logger.info("processing %s at %s on %s" % (self.pair, self.exchg, self.tick))

        if self.tick not in ticks.keys():
            raise RuntimeError('unknown tick %s for bittrex' % self.tick)

        from libyams.orm.models import TickerData
        from django.db import IntegrityError

        counter = 0
        max_tries = 5
        max_wait = random.sample(xrange(15), 1)[0]

        # TODO: set index on TickerData.{market, tick_len}
        t1 = time.time()
        td_all = TickerData.objects.filter(market=self.pair, tick_len=self.tick)
        td_count_before = len(td_all)
        t2 = time.time()
        logger.debug("TIME (td_count_before) of processing %s at %s on %s was %s sec" % ( self.pair, self.exchg.name, self.tick, str(t2 - t1)))

        while counter < max_tries:
            t1 = time.time()
            to_insert = []
            # for d in data[:5]:
            for d in self.data:
                # t = TickerData(market=self.market, tick_len=self.tick, time_val=d['T'], open=d['O'], high=d['H'], low=d['L'], close=d['C'])

                t = TickerData.objects.filter(market=self.pair, tick_len=self.tick, time_val=d['time_val'])

                # logger.debug("d: %s" % d)
                # logger.debug("t: %s" % t)

                if not t.exists():
                # if t not in td_all: #not TickerData.objects.filter(market=self.market, tick_len=self.tick, time_val=d['T'], open=d['O'], high=d['H'], low=d['L'], close=d['C']).exists():
                    # print "adding row", d['C']
                    to_insert.append({
                        'market': self.market,
                        'tick_len': self.tick,
                        'time_val': d['T'],
                        'open': float(d['O']),
                        'high': float(d['H']),
                        'low': float(d['L']),
                        'close': float(d['C'])
                    })

            print len(to_insert)

            TickerData.objects.bulk_create([
                TickerData(**i) for i in to_insert
            ])

            t2 = time.time()
            logger.debug("TIME (save data to db) of processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2 - t1)))

            # check if we got new data, if not try again in 7 seconds
            t1 = time.time()
            td_count_after = len(TickerData.objects.filter(market=self.market, tick_len=self.tick))
            t2 = time.time()
            logger.debug("TIME (td_count_after) of processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2 - t1)))

            logger.debug("count before %s" % td_count_before)
            logger.debug("count after  %s" % td_count_after)

            if td_count_after > td_count_before:
                counter = max_tries
            else:
                logger.info("AGAIN (wait %d s, counter: %d) processing %s at %s on %s" % (max_wait, counter, self.pair, self.exchg.name, self.tick))
                counter = counter + 1
                time.sleep(max_wait)

        logger.info("finished processing %s at %s on %s" % (self.pair, self.exchg.name, self.tick))
        time.sleep(.5)

    def run(self):
        # >> > total_time = timeit.timeit('[v for v in range(10000)]', number=10000)
        t1 = time.time()
        self.doit()
        t2 = time.time()
        logger.debug("TIME of processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2-t1)))


#
# worker thread for analysis
#
class WorkerThread(threading.Thread):
    def __init__(self, q):
        threading.Thread.__init__(self)
        self.queue = q
        self.name = "-WorkerThread-"

    def run(self):
        # TODO: check for exceptions
        logger.debug("starting analysis worker thread")
        while True:
            itm = self.queue.get()  # if there is no item, this will wait

            if "exchange" not in itm.keys() or "pair" not in itm.keys() or "tick" not in itm.keys() or "data" not in itm.keys():
                logger.debug("data in wrong format, aborting...")
                continue

            logger.debug("got valid data (len: %s) from '%s'-tracker for '%s'" % (len(itm['data']), itm['exchange'], itm['tick']))

            # TODO: check for thread timeout
            if len(thrds_save) >= CONFIG["general"]["limit_threads_recv"]:
                for x in thrds_save:
                    x.join()
                    thrds_save.remove(x)

            t = SaveTickerData(itm['exchange'], itm['pair'], itm['tick'], itm['data'])
            thrds_save.append(t)
            # t.daemon = True
            t.start()

            self.queue.task_done()
            logger.debug("finished processing item %s" % itm['pair'])


#
# worker thread for analysis
#
class InitDBThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global CON_REDIS

        check_fn = '/tmp/FIRST_START'
        if os.path.exists(check_fn):
            logger.info("waiting for db to finish starting")
            time.sleep(25)
            os.remove(check_fn)

        time.sleep(5)

        # bootstrap ORM
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
        execute_from_command_line([sys.argv[0], 'makemigrations'])
        execute_from_command_line([sys.argv[0], 'migrate'])
        django.setup()

        CON_REDIS.set('STATUS_RECV', True)

        return


#
# MAiN
#
if __name__ == "__main__":

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['general']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # start
    if CONFIG["general"]["production"]:
        logger.info("setup redis connection")
        CON_REDIS = redis.Redis(host=CONFIG["general"]["redis"]["host"], port=CONFIG["general"]["redis"]["port"], db=0)
        CON_REDIS.set('STATUS_RECV', False)

        logger.info("start init_db()")
        t1 = InitDBThread()
        t1.start()
        time.sleep(.5)

        logger.info("start worker thread")
        t2 = WorkerThread(queue_save)
        t2.start()
