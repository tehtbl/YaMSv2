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
import json
import logging
import threading

from pytz import utc
from operator import itemgetter

from apscheduler.schedulers.background import BackgroundScheduler

from libyams.utils import get_conf, tickers, get_btc_usd

from exchanges import get_exchange_obj

import pprint
pp = pprint.PrettyPrinter(indent=2)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()


#
#
#
class SaveTickerData(threading.Thread):
    def __init__(self, pair, tick):
        threading.Thread.__init__(self)
        self.pair = pair
        self.tick = tick

    def run(self):
        # TODO: check for exceptions
        logger.info("processing %s at %s" % (self.pair, self.tick))

        time.sleep(3)

        logger.info("finished processing %s at %s" % (self.pair, self.tick))
        time.sleep(.5)


#
# data receiving method
#
def recv_data(exchg, tick):
    thrds = []

    ex = get_exchange_obj(exchg)

    print ex

    logger.info("getting related currencies from market summary")
    for cur in ex.get_related_markets():
        pair = cur['Summary']['MarketName']

        # TODO: check for thread timeout
        if len(thrds) >= CONFIG["General"]["limit_threads_recv"]:
            for x in thrds:
                x.join()
                thrds.remove(x)

        t = SaveTickerData(pair, tick)
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

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['General']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # if CONFIG['telegram']['enabled']:
    #     TelegramHandler.listen()
    #     TelegramHandler.send_msg('*Status:* `scanner started`')

    if not CONFIG["General"]["production"]:
        logger.info(">>> DEVELOPMENT MODE, NO SCHEDULING <<<")
        recv_data('bittrex', '5m')
        os._exit(0)

    if not len(CONFIG["DataTracker"]["exchanges"]) > 0:
        logger.info(">>> no exchanges defined, exiting... <<<")
        os._exit(0)

    # production mode: set scheduling of executing receiver methods
    if CONFIG["General"]["production"]:
        scheduler = BackgroundScheduler(timezone=utc, job_defaults={
            'max_instances': 10
        })

        # prepare scheduler
        for exchg in CONFIG["DataTracker"]["exchanges"]:
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