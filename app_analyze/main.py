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
import imp
import json
import time
import arrow
import redis
import django
import os.path
import logging
import datetime
import threading
import talib.abstract as ta

from operator import itemgetter
from pandas import DataFrame
from wrapt import synchronized

from libyams.utils import get_conf

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = get_conf()
plugins = {}


#
# populate indicators to dataframe
#
@synchronized
def populate_indicators(dataframe):

    dataframe['cci14'] = ta.CCI(dataframe, 14)
    dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
    dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)

    dataframe['ema33'] = ta.EMA(dataframe, timeperiod=33)
    dataframe['sar'] = ta.SAR(dataframe, 0.02, 0.22)
    dataframe['adx'] = ta.ADX(dataframe)

    stochrsi = ta.STOCHRSI(dataframe)
    dataframe['stochrsi'] = stochrsi['fastd']  # values between 0-100, not 0-1

    macd = ta.MACD(dataframe)
    dataframe['macd'] = macd['macd']
    dataframe['macds'] = macd['macdsignal']
    dataframe['macdh'] = macd['macdhist']

    return dataframe


#
# analysis thread
#
class CalcIndicators(threading.Thread):
    def __init__(self, pair, fn, tick):
        threading.Thread.__init__(self)
        self.pair = pair
        self.fn = fn
        self.tick = tick
        self.name = "-CalcIndicators-%s_%s" % (self.pair, self.tick)

    def run(self):
        logger.debug("analyzing %s at %s" % (self.fn, self.tick))


        # TODO

        # calc all indicators for tickdata object, instantiate an indicator object with all indicators



        # # TODO: still needed/wanted?!
        # #
        # # check for last price drop
        # #
        # if self.tick == "FiveMin":
        #     dataframe = parse_ticker_dataframe(data)
        #     latest = dataframe.iloc[-1]
        #
        #     old_val = float(dataframe.iloc[-2]['close'])
        #     new_val = float(dataframe.iloc[-1]['close'])
        #     diff = float(((old_val - new_val) / old_val) * -100)
        #
        #     if abs(diff) > 10 and diff < 0:
        #         tdiff = arrow.utcnow() - arrow.get(latest['date'])
        #         msg = msg_price_chg % ( self.pair, diff, tdiff,
        #
        #                                 old_val, new_val,
        #
        #                                 self.pair
        #                             )
        #
        #         logger.info(msg)
        # else:
        #
        # check for signals from plugins
        #
        for p in plugins[self.tick]:
            logger.debug("analysing with plugin: %s" % (p['name']))

            plugin_exec = imp.load_module(p['name'], *p["info"])
            dataframe, info = plugin_exec.populate_indicators_and_buy_signal(parse_ticker_dataframe(data))

            # print info

            signal = False
            latest = dataframe.iloc[-1]

            if latest['buy'] == 1:
                signal = True

            logger.info('buy_trigger: %s (pair=%s, tick=%s, strat=%s, signal=%s)', latest['date'], self.pair, self.tick, p['name'], signal)
            # logger.debug(latest)

            if signal:
                threePercent = latest['close'] + ((latest['close']/100) * 3)
                fivePercent = latest['close'] + ((latest['close']/100) * 5)
                tenPercent = latest['close'] + ((latest['close']/100) * 10)

                msg = msg_buysignal % ( self.pair,

                                        latest['close'],
                                        threePercent,
                                        fivePercent,
                                        tenPercent,

                                        self.tick,
                                        info,

                                        self.pair
                                    )

                logger.info(msg)

        logger.debug("finished analyzing %s at %s" % (self.fn, self.tick))
        time.sleep(.5)


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

                    # app_analyze_1    | 2017-11-10 14:08:34,298 - __main__ - DEBUG - {u'xchg': u'btrx', u'pair': u'BTC-1ST', u'tick': u'5m', u'data': [{u'high': 4.277e-05, u'close': 4.277e-05, u'open': 4.25e-05, u'tval': u'2017-10-21T20:10:00', u'low': 4.25e-05}, {u'high': 4.277e-05, u'close': 4.277e-05, u'open': 4.239e-05, u'tval': u'2017-10-21T20:15:00', u'low': 4.239e-05}, {u'high': 4.277e-05, u'close': 4.277e-05, u'open': 4.277e-05, u'tval': u'2017-10-21T20:20:00', u'low': 4.277e-05}]}
                    # logger.debug(itm)
                    # logger.debug(itm['data'])
                    # logger.debug(TickerData.objects.all())

                    logger.debug("analyzing %s at %s on %s" % (itm['pair'], itm['xchg'], itm['tick']))

                    if itm['xchg'] == CONFIG['bittrex']['short']:
                        t1 = time.time()
                        df = populate_indicators(DataFrame(list(TickerData.objects.all().values())))
                        t2 = time.time()
                        logger.debug("TIME of populating indicators for %s at %s on %s was %s sec" % (itm['pair'], itm['xchg'], itm['tick'], str(t2 - t1)))

                        # logger.debug(df)

                    logger.debug("finished analyzing %s at %s on %s" % (itm['pair'], itm['xchg'], itm['tick']))

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
    PUBSUB = rcon.pubsub()

    # check if data tracker is ready for storing and sending data
    rcon.publish(CONFIG["general"]["redis"]["chans"]["db_heartbeat_ctrl"], 'db_ready')
    PUBSUB.subscribe(CONFIG["general"]["redis"]["chans"]["db_heartbeat"])
    while True:
        msg = PUBSUB.get_message()

        # logger.debug("received msg type:" + str(type(msg)))
        # logger.debug("received msg:" + str(msg))

        if isinstance(msg, dict) and msg['type'] == 'message' and msg['channel'] == CONFIG["general"]["redis"]["chans"][
            "db_heartbeat"]:
            itm = json.loads(msg['data'])

            logger.debug("db heartbeat info %s" % itm)

            if itm['state'] and (int(time.time()) - int(itm['time'])) < 30:
                break

        logger.info("tracker not yet ready, waiting another 5s...")
        rcon.publish(CONFIG["general"]["redis"]["chans"]["db_heartbeat_ctrl"], 'db_ready')
        time.sleep(5)

    # bootstrap ORM
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "libyams.settings")
    django.setup()

    from libyams.orm.models import TickerData, Indicator

    logger.info("start WorkerThread()")
    wt = WorkerThread(rcon)
    wt.start()
    time.sleep(.5)
