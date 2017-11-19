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
import traceback
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
def save_to_influxdb(con, df, measurement):
    # duplicates will be overwritten:
    # https://docs.influxdata.com/influxdb/v1.3/troubleshooting/frequently-asked-questions/#how-does-influxdb-handle-duplicate-points

    # logger.debug("influx infos:")
    # logger.debug(con.get_list_database())
    # logger.debug(con.get_list_users())

    df.fillna(0, inplace=True)
    # con.write_points(df, 'all')
    # logger.debug(df[:5].to_json(orient='records'))
    df_json = df.to_json(orient='records')
    # logger.debug(df_json)

    # json_body = [
    #     {
    #         "measurement": "cpu_load_short",
    #         "tags": {
    #             "host": "server01",
    #             "region": "us-west"
    #         },
    #         "time": "2009-11-10T23:00:00Z",
    #         "fields": {
    #             "Float_value": 0.64,
    #             "Int_value": 3,
    #             "String_value": "Text",
    #             "Bool_value": True
    #         }
    #     }
    # ]

    tag_keys = [
        "pair",
        "tick",
        "xchg",
    ]

    json_to_send = []
    for d in json.loads(df_json):
        tags = {}
        fields = {}
        for i in d.keys():
            if i in tag_keys:
                tags[i] = d[i]
            else:
                fields[i] = d[i]

        json_to_send.append({
            "measurement": measurement,
            "tags": tags,
            "time": int(d["tval"]),
            "fields": fields
        })

    # logger.debug(json_to_send[:5])

    # con.write_points(df, measurements)
    # con.write_points(json.dumps(json_to_send))
    con.write_points(json_to_send)

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
        self.limit_tickerdata = int(CONFIG["general"]["limit_tickerdata"])
        self.runner = True

    def run(self):
        global CONFIG

        self.redis_pubsub.subscribe(CONFIG["general"]["redis"]["chans"]["data_analyzer"])

        while self.runner:
            msg = self.redis_pubsub.get_message()

            # logger.debug(msg)

            if isinstance(msg, dict) and msg['type'] == 'message':
                if msg['channel'] == CONFIG["general"]["redis"]["chans"]["data_analyzer"]:
                    itm = json.loads(msg['data'])['data']

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

                        objs = TickerData.objects.all().values('pk', 'xchg', 'pair', 'tick', 'tval', 'open', 'high', 'low', 'close').order_by('-tval')[:self.limit_tickerdata]
                        # logger.debug(objs)
                        # df = DataFrame.from_records(objs, index='tval')
                        # df = DataFrame.from_records(objs)
                        df = DataFrame.from_records(objs, index='pk')
                        df.head()

                        # all_ticks = list(TickerData.objects.all().values())[:5]
                        # df = populate_indicators(DataFrame(all_ticks))
                        new_df = populate_indicators(df)

                        t2 = time.time()
                        logger.debug("TIME of populating indicators for %s at %s on %s was %s sec" % (itm['pair'], itm['xchg'], itm['tick'], str(t2 - t1)))

                        # logger.debug(new_df[:5])

                        try:
                            # tag = "%s-%s-%s" % (itm['xchg'], itm['pair'], itm['tick'])
                            # save_to_influxdb(self.inflx_con, new_df, tag)
                            save_to_influxdb(self.inflx_con, new_df, itm['xchg'])
                        except Exception:
                            logger.debug("TRACEBACK for SAVING TO INFLUXDB")
                            logger.debug(traceback.print_exc())

                    logger.debug("finished analyzing %s at %s on %s" % (itm['pair'], itm['xchg'], itm['tick']))

                    if not CONFIG["general"]["production"]:
                        self.runner = False

            time.sleep(.5)


#
# db check thread for analysis
#
class DBCheckThread(threading.Thread):
    def __init__(self, redis_con):
        threading.Thread.__init__(self)
        self.redis_con = redis_con
        self.runner = True

    def run(self):
        global TRACKER_ALIVE

        TRACKER_ALIVE = False
        while self.runner:
            try:
                itm = json.loads(self.redis_con.get(CONFIG["general"]["redis"]["vars"]["hb_tracker"]))

                logger.debug("db heartbeat info %s" % itm)
                if itm['state'] and (int(time.time()) - int(itm['time'])) < 15:
                    TRACKER_ALIVE = True
                else:
                    TRACKER_ALIVE = False
            except:
                pass

            time.sleep(5)


#
# MAiN
#
if __name__ == "__main__":

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['general']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    logger.debug("setup redis connection")
    rcon = redis.StrictRedis(host=CONFIG["general"]["redis"]["host"], port=CONFIG["general"]["redis"]["port"], db=0)

    logger.debug("start HeartBeatThread()")
    dbt = DBCheckThread(rcon)
    dbt.start()
    time.sleep(.5)

    while not TRACKER_ALIVE:
        time.sleep(.5)

    # bootstrap ORM
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "libyams.settings")
    django.setup()
    from libyams.orm.models import TickerData, Indicator

    # TODO: make loop to wait for influxdb up and running, not needed atm because it is starting while db is starting which takes enough time
    # inflx_con = DataFrameClient(CONFIG["general"]["influxdb"]["host"],
    inflx_con = InfluxDBClient(CONFIG["general"]["influxdb"]["host"],
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
