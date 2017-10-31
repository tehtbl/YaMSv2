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

import sys
import json
import time
import logging
import threading
import requests as req

from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

from libyams.utils import get_conf, ticks, get_btc_usd

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()


#
# get available markets
#
def get_markets():
    url = "https://bittrex.com/api/v2.0/pub/Markets/GetMarketSummaries"
    r = req.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    })
    data = r.json()
    if not data["success"]:
        raise RuntimeError("BITTREX: {}".format(data["message"]))

    # return map(lambda x: x['Summary']['MarketName'], data['result'])
    return data['result']


#
# get related currencies
#
def get_related_currencies():
    rel_curr = []
    btc_usd_price = get_btc_usd()

    # filter out related currencies
    for c in get_markets():
        if c['Market']['MarketCurrency'] not in CONFIG["bittrex"]["blacklist"]:
            val = c['Summary']['Last'] * btc_usd_price
            if CONFIG["bittrex"]["min_price_usd"] < val < CONFIG["bittrex"]["max_price_usd"]:
                if CONFIG["bittrex"]["stake_currency_enabled"]:
                    if c['Market']['BaseCurrency'] == CONFIG["bittrex"]["stake_currency"]:
                        rel_curr.append(c)
                else:
                    rel_curr.append(c)

    return map(lambda x: x['Summary']['MarketName'], rel_curr)


#
# get data from BITTREX ticker
#
def get_ticker_data(pair, tick):
    url = 'https://bittrex.com/Api/v2.0/pub/market/GetTicks'
    params = {
        'marketName': pair,
        'tickInterval': tick,
    }

    r = req.get(url, params=params, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    })

    data = r.json()
    if not data['success']:
        raise RuntimeError('BITTREX: {}'.format(data['message']))

    return data['result']


#
# thread for saving data to database
#
class SendTickerData(threading.Thread):
    def __init__(self, pair, tick):
        threading.Thread.__init__(self)
        self.pair = pair
        self.tick = tick
        self.exchg = CONFIG["bittrex"]["short"]

    def doit(self):
        logger.info("processing %s at %s on %s" % (self.pair, self.exchg, self.tick))

        if self.tick not in ticks.keys():
            raise RuntimeError('unknown tick %s for bittrex' % self.tick)

        data = get_ticker_data(self.pair, CONFIG["bittrex"]["tickers"][self.tick])

        to_insert = []
        for d in data[:5]:
            to_insert.append({
                'market': self.pair,
                'tick_len': self.tick,
                'time_val': d['T'],
                'open': float(d['O']),
                'high': float(d['H']),
                'low': float(d['L']),
                'close': float(d['C'])
            })

        # TODO: check if new data is there
        # TODO: send data to socket for data controller
        # Example:
        #     {
        #         'exchange': self.name,
        #         'market': 'BTC-XVG'
        #         'tick': '5m'
        #         'data': [
        #             {
        #                 'open': ...
        #                 'close': ...
        #                 'high': ...
        #                 'low': ...
        #                 'timestamp': ...
        #             }
        #         ]
        #     }

        import socket
        import sys

        HOST, PORT = "localhost", 9999
        data = " ".join(sys.argv[1:])

        # Create a socket (SOCK_STREAM means a TCP socket)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Connect to server and send data
            sock.connect((HOST, PORT))
            sock.sendall(data + "\n")

            # Receive data from the server and shut down
            received = sock.recv(1024)
        finally:
            sock.close()

        print "Sent:     {}".format(data)
        print "Received: {}".format(received)

        # logger.debug(to_insert)
        time.sleep(1)

        logger.info("finished processing %s at %s on %s" % (self.pair, self.exchg, self.tick))
        time.sleep(.5)

    def run(self):
        t1 = time.time()
        self.doit()
        t2 = time.time()
        logger.debug("TIME of processing %s at %s on %s was %s sec" % (self.pair, self.exchg, self.tick, str(t2-t1)))


#
# data receiving method
#
def recv_data(tick):
    thrds = []

    logger.info("getting related currencies from market summary")
    for pair in get_related_currencies():
        if len(thrds) >= CONFIG["general"]["limit_threads_recv"]:
            t = thrds[0]
            t.join()
            thrds.remove(t)

            # for x in thrds:
            #     x.join()
            #     thrds.remove(x)

        t = SendTickerData(pair, tick)
        thrds.append(t)
        t.start()

        if not CONFIG["general"]["production"]:
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
    if CONFIG['general']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # check for exchanges
    if "bittrex" not in CONFIG["datatracker"]["exchanges"] or "bittrex" not in CONFIG.keys():
        logger.info(">>> no bittrex exchange defined, exiting... <<<")
        sys.exit(0)

    # check for status
    if not CONFIG["bittrex"]["enabled"]:
        logger.info(">>> bittrex exchange not enabled, exiting... <<<")
        sys.exit(0)

    # development mode
    if not CONFIG["general"]["production"]:
        logger.info(">>> DEVELOPMENT MODE, NO SCHEDULING <<<")
        recv_data('5m')
        sys.exit(0)


    # TODO: check if data tracker is ready!!!



    # production mode: set scheduling of executing receiver methods
    if CONFIG["general"]["production"]:
        scheduler = BackgroundScheduler(timezone=utc, job_defaults={
            'max_instances': 10
        })

        # start receiver methods for the first time to initialize data
        for t in CONFIG["bittrex"]["tickers"]:
            recv_data(t)

        # wait some seconds until data is finished aggregating at bittrex-side
        scheduler.add_job(recv_data, args=['5m'], trigger='cron', minute="*/5", second="7")
        scheduler.add_job(recv_data, args=['30m'], trigger='cron', minute="*/30", second="13")
        scheduler.add_job(recv_data, args=['1h'], trigger='cron', hour="*/4", minute="2", second="21")
        scheduler.add_job(recv_data, args=['1d'], trigger='cron', hour="0", minute="5", second="29")

        # start the scheduler
        scheduler.start()

        try:
            # This is here to simulate application activity (which keeps the main thread alive).
            while True:
                time.sleep(2)

        except (KeyboardInterrupt, SystemExit):
            # Not strictly necessary if daemonic mode is enabled but should be done if possible
            scheduler.shutdown()