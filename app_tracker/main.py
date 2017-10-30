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
import cgi
import json
import time
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
STATUS_RECV = False

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
    def __init__(self, exchange, market, tick, data):
        threading.Thread.__init__(self)
        self.exchg = exchange
        self.market = market
        self.tick = tick
        self.data = data

    def doit(self):
        logger.info("processing %s at %s on %s" % (self.market, self.exchg, self.tick))

        if self.tick not in ticks.keys():
            raise RuntimeError('unknown tick %s for bittrex' % self.tick)

        from libyams.orm.models import TickerData
        from django.db import IntegrityError

        counter = 0
        max_tries = 5
        max_wait = random.sample(xrange(15), 1)[0]

        t1 = time.time()
        td_all = TickerData.objects.filter(market=self.market, tick_len=self.tick)
        td_count_before = len(td_all)
        t2 = time.time()
        logger.debug("TIME (td_count_before) of processing %s at %s on %s was %s sec" % ( self.pair, self.exchg.name, self.tick, str(t2 - t1)))

        while counter < max_tries:
            t1 = time.time()
            data = self.exchg.get_ticker_data(self.pair, self.tick)
            # logger.debug(data[:2])
            t2 = time.time()
            logger.debug("TIME (get data) of processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2 - t1)))

            t1 = time.time()
            # for d in data:
            #     # t = TickerData(market=self.market, tick_len=self.tick, time_val=d['T'],
            #     #                open=d['O'], high=d['H'], low=d['L'], close=d['C'])
            #     #
            #     # if t not in td_all.iterator():
            #     #     try:
            #     #         t.save()
            #     #     except IntegrityError:
            #     #         pass
            #
            #     t, created = TickerData.objects.get_or_create(market=self.market, tick_len=self.tick, time_val=d['T'], open=d['O'], high=d['H'], low=d['L'], close=d['C'])
            #     if created:
            #         logger.debug("OBJ created while processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2 - t1)))

            to_insert = []
            # for d in data[:5]:
            for d in data:
                # t = TickerData(market=self.market, tick_len=self.tick, time_val=d['T'], open=d['O'], high=d['H'], low=d['L'], close=d['C'])

                t = TickerData.objects.filter(market=self.market, tick_len=self.tick, time_val=d['T'])

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


        # while not check and counter < 3:
        #     t1 = time.time()
        #     data = self.exchg.get_ticker_data(self.pair, self.tick)
        #     # logger.debug(data[:2])
        #     t2 = time.time()
        #     logger.debug("TIME (get data) of processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2 - t1)))
        #
        #     t1 = time.time()
        #     to_insert = []
        #     for d in data:
        #         # t = TickerData(market=self.market, tick_len=self.tick, time_val=d['T'],
        #         #                open=d['O'], high=d['H'], low=d['L'], close=d['C'])
        #         to_insert.append({
        #             'market': self.market,
        #             'tick_len': self.tick,
        #             'time_val': d['T'],
        #             'open': d['O'],
        #             'high': d['H'],
        #             'low': d['L'],
        #             'close': d['C']
        #         })
        #
        #         # try:
        #         #     t.save()
        #         # except IntegrityError:
        #         #     pass
        #
        #     # TickerData.objects.bulk_create([
        #     #     TickerData(**i) for i in to_insert
        #     # ])
        #
        #     t2 = time.time()
        #     logger.debug("TIME (save data to db) of processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2 - t1)))

        # # check if we got new data, if not try again in 7 seconds
        # t1 = time.time()
        # td_count_after = len(TickerData.objects.all())
        # t2 = time.time()
        # logger.debug("TIME (td_count_after) of processing %s at %s on %s was %s sec" % (self.pair, self.exchg.name, self.tick, str(t2 - t1)))
        #
        # logger.debug(td_count_before)
        # logger.debug(td_count_after)
        #
        #     # if td_count_after > td_count_before:
        #     #     check = True
        #     # else:
        #     #     logger.debug(td_count_before)
        #     #     logger.debug(td_count_after)
        #     #     logger.info("AGAIN (counter: %d) processing %s at %s on %s" % (counter, self.pair, self.exchg.name, self.tick))
        #     #     counter = counter + 1
        #     #     time.sleep(30)

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

            if "exchange" not in itm.keys() or "market" not in itm.keys() or "tick" not in itm.keys() or "data" not in itm.keys():
                logger.debug("data in wrong format, aborting...")
                continue

            # TODO: check for thread timeout
            if len(thrds_save) >= CONFIG["general"]["limit_threads_recv"]:
                for x in thrds_save:
                    x.join()
                    thrds_save.remove(x)

            t = SaveTickerData(itm['exchange'], itm['market'], itm['tick'], itm['data'])
            thrds_save.append(t)
            # t.daemon = True
            t.start()

            self.queue.task_done()
            logger.debug("finished processing item %s" % itm['pair'])


#
#
#
class WebHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        global STATUS_RECV

        ret_msg = ""

        if self.path == '/status':
            ret_msg = json.dumps({
                'status': STATUS_RECV
            })

        ret_msg = ret_msg + "\r\n"

        self._set_headers()
        self.wfile.write(ret_msg)

        return

    def do_POST(self):
        # Parse the form data posted
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': self.headers['Content-Type']
            })

        # Begin the response
        self.send_response(200)
        self.end_headers()
        self.wfile.write('Client: %s\n' % str(self.client_address))
        self.wfile.write('User-agent: %s\n' % str(self.headers['user-agent']))
        self.wfile.write('Path: %s\n' % self.path)
        self.wfile.write('Form data:\n')

        # Echo back information about what was posted in the form
        for field in form.keys():
            field_item = form[field]
            if field_item.filename:
                # The field contains an uploaded file
                file_data = field_item.file.read()
                file_len = len(file_data)
                del file_data
                self.wfile.write('\tUploaded %s as "%s" (%d bytes)\n' % \
                        (field, field_item.filename, file_len))
            else:
                # Regular form value
                self.wfile.write('\t%s=%s\n' % (field, form[field].value))
        return


#
# worker thread for analysis
#
class InitDBThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global STATUS_RECV

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

        STATUS_RECV = True

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
        logger.info("start init_db()")
        t1 = InitDBThread()
        t1.start()
        time.sleep(.5)

        logger.info("start worker thread")
        t2 = WorkerThread(queue_save)
        t2.start()
        time.sleep(.5)

        logger.info("starting web server")
        server = HTTPServer(("0.0.0.0", CONFIG["datatracker"]["connection"]["port"]), WebHandler)
        server.serve_forever()
