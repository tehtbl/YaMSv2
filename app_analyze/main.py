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
from django.forms import model_to_dict
from influxdb import InfluxDBClient, DataFrameClient


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
# save data to influxdb
#
def save_to_influxdb(con, df, tag):
    # duplicates will be overwritten:
    # https://docs.influxdata.com/influxdb/v1.3/troubleshooting/frequently-asked-questions/#how-does-influxdb-handle-duplicate-points

    # logger.debug("influx infos:")
    # logger.debug(con.get_list_database())
    # logger.debug(con.get_list_users())

    df.fillna(0, inplace=True)
    con.write_points(df, tag)

    return


#
# worker thread for analysis
#
class WorkerThread(threading.Thread):
    def __init__(self, redis_con, inflx_con):
        threading.Thread.__init__(self)
        self.redis_con = redis_con
        self.redis_pubsub = redis_con.pubsub()
        self.inflx_con = inflx_con
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

                    # app_analyze_1    | 2017-11-10 14:08:34,298 - __main__ - DEBUG - {u'xchg': u'btrx', u'pair': u'BTC-1ST', u'tick': u'5m', u'data': []}
                    # logger.debug(itm)
                    # logger.debug(itm['data'])
                    # logger.debug(TickerData.objects.all())

                    logger.debug("analyzing %s at %s on %s" % (itm['pair'], itm['xchg'], itm['tick']))

                    if itm['xchg'] == CONFIG['bittrex']['short']:
                        t1 = time.time()

                        objs = TickerData.objects.all().values('xchg', 'pair', 'tick', 'tval', 'open', 'high', 'low', 'close')
                        # logger.debug(objs)
                        df = DataFrame.from_records(objs, index='tval')
                        df.head()

                        # all_ticks = list(TickerData.objects.all().values())[:5]
                        # df = populate_indicators(DataFrame(all_ticks))
                        new_df = populate_indicators(df)

                        # df = populate_indicators(DataFrame(list(TickerData.objects.all().values())))
                        t2 = time.time()
                        logger.debug("TIME of populating indicators for %s at %s on %s was %s sec" % (itm['pair'], itm['xchg'], itm['tick'], str(t2 - t1)))

                        # try:
                        #     logger.debug(new_df)
                        #     logger.debug(save_to_influxdb(self.inflx_con, new_df))
                        # except Exception:
                        #     import traceback
                        #     traceback.print_exc()

                        tag = "%s-%s-%s" % (itm['xchg'], itm['pair'], itm['tick'])
                        save_to_influxdb(self.inflx_con, new_df, tag)

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

        if isinstance(msg, dict) and msg['type'] == 'message' and msg['channel'] == CONFIG["general"]["redis"]["chans"]["db_heartbeat"]:
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

    # TODO: make loop to wait for influxdb up and running, not needed atm because it is starting while db is starting which takes enough time
    inflx_con = DataFrameClient(CONFIG["general"]["influxdb"]["host"],
                                CONFIG["general"]["influxdb"]["port"],
                                CONFIG["general"]["influxdb"]["usr"],
                                CONFIG["general"]["influxdb"]["pwd"],
                                CONFIG["general"]["influxdb"]["db"])

    inflx_con.create_database(CONFIG["general"]["influxdb"]["db"])
    inflx_con.create_user(CONFIG["general"]["influxdb"]["usr"], CONFIG["general"]["influxdb"]["pwd"])

    logger.debug("influx infos:")
    logger.debug(inflx_con.get_list_database())
    logger.debug(inflx_con.get_list_users())

    logger.info("start WorkerThread()")
    wt = WorkerThread(rcon, inflx_con)
    wt.start()
    time.sleep(.5)
