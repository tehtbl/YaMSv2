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
import time
import random
import django
import logging
import threading

from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

from libyams.utils import get_conf, ticks
from exchanges import get_exchange_obj

import pprint
pp = pprint.PrettyPrinter(indent=2)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

CONFIG = get_conf()


#
# thread for saving data to database
#
class SaveTickerData(threading.Thread):
    def __init__(self, ex, pair, tick, market):
        threading.Thread.__init__(self)
        self.exchg = ex
        self.pair = pair
        self.tick = tick
        self.market = market

    def doit(self):
        logger.info("processing %s at %s on %s" % (self.pair, self.exchg.name, self.tick))

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
# data receiving method
#
def recv_data(exchg, tick):
    thrds = []

    ex = get_exchange_obj(exchg)

    if not ex:
        logger.debug("got no exchange object, exiting")
        return False

    from libyams.orm.models import Market

    logger.info("getting related currencies from market summary")
    for pair in ex.get_markets():
        m, created = Market.objects.get_or_create(exchange=ex.name, pair=pair)

        if len(thrds) >= CONFIG["General"]["limit_threads_recv"]:
            t = thrds[0]
            t.join()
            thrds.remove(t)

            # for x in thrds:
            #     x.join()
            #     thrds.remove(x)

        t = SaveTickerData(ex, pair, tick, m)
        thrds.append(t)
        t.start()

        if not CONFIG["General"]["production"]:
            return

    for x in thrds:
        x.join()
        thrds.remove(x)

    return True


#
# MAiN
#
if __name__ == "__main__":

    # logger.info("waiting for db to finish starting")
    # time.sleep(20)

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['General']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # check for exchanges
    if not len(CONFIG["DataTracker"]["exchanges"]) > 0:
        logger.info(">>> no exchanges defined, exiting... <<<")
        os._exit(0)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    django.setup()

    # development mode
    if not CONFIG["General"]["production"]:
        logger.info(">>> DEVELOPMENT MODE, NO SCHEDULING <<<")
        # recv_data('bittrex', '4h')
        # recv_data('bitfinex', '4h')
        # recv_data('bittrex', '30m')
        recv_data('bittrex', '5m')
        import sys
        sys.exit(0)
        # os._exit(0)

    # production mode: set scheduling of executing receiver methods
    if CONFIG["General"]["production"]:
        scheduler = BackgroundScheduler(timezone=utc, job_defaults={
            'max_instances': 10
        })

        # prepare scheduler
        for exchg in CONFIG["DataTracker"]["exchanges"]:

            # start receiver methods for the first time to initialize data
            for t in ticks:
                recv_data(exchg, t)

            # wait some seconds until data is finished aggregating at bittrex-side
            scheduler.add_job(recv_data, args=(exchg, '5m'), trigger='cron', minute="*/5", second="7")
            scheduler.add_job(recv_data, args=(exchg, '30m'), trigger='cron', minute="*/30", second="13")
            scheduler.add_job(recv_data, args=(exchg, '4h'), trigger='cron', hour="*/4", minute="2", second="7")
            scheduler.add_job(recv_data, args=(exchg, '1d'), trigger='cron', hour="0", minute="5", second="13")

        # start the scheduler
        scheduler.start()

        try:
            # This is here to simulate application activity (which keeps the main thread alive).
            while True:
                time.sleep(2)

        except (KeyboardInterrupt, SystemExit):
            # Not strictly necessary if daemonic mode is enabled but should be done if possible
            scheduler.shutdown()
