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
import django
import logging
import threading

from pytz import utc
from django.conf import settings
from django.core.management import execute_from_command_line
from apscheduler.schedulers.background import BackgroundScheduler

from libyams.utils import get_conf, ticks
from exchanges import get_exchange_obj

import pprint
pp = pprint.PrettyPrinter(indent=2)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

CONFIG = get_conf()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

settings.configure(
    INSTALLED_APPS=[
        'libyams.orm',
    ],
    DATABASES={
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
    },
)


#
#
#
class SaveTickerData(threading.Thread):
    def __init__(self, ex, pair, tick):
        threading.Thread.__init__(self)
        self.exchg = ex
        self.pair = pair
        self.tick = tick

    def run(self):
        # TODO: check for exceptions
        logger.info("processing %s at %s on %s" % (self.pair, self.exchg.name, self.tick))



        data = self.exchg.get_ticker_data(self.pair, self.tick)
        logger.debug(data)

        # >>> import libyams.django_manage
        # >>> from libyams.orm.models import Settings
        # >>>
        # >> > s = Settings.objects.create(base_currency='btc')

        from libyams.orm.models import Settings
        s = Settings.objects.create(base_currency='btc')
        s.save()

        logger.info("obj: " + str(Settings.objects.all()))

        logger.info("finished processing %s at %s on %s" % (self.pair, self.exchg.name, self.tick))
        time.sleep(.5)


#
# data receiving method
#
def recv_data(exchg, tick):
    thrds = []

    ex = get_exchange_obj(exchg)

    if not ex:
        logger.debug("got no exchange object, exiting")
        return False

    logger.info("getting related currencies from market summary")
    for cur in ex.get_markets():
        pair = cur['Summary']['MarketName']

        # TODO: check for thread timeout
        if len(thrds) >= CONFIG["General"]["limit_threads_recv"]:
            for x in thrds:
                x.join()
                thrds.remove(x)

        t = SaveTickerData(ex, pair, tick)
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

    logger.info("waiting for db to finish starting")
    time.sleep(30)

    # set log level
    logger.setLevel(logging.INFO)
    if CONFIG['General']['loglevel'] == 'debug':
        logger.setLevel(logging.DEBUG)

    # check for exchanges
    if not len(CONFIG["DataTracker"]["exchanges"]) > 0:
        logger.info(">>> no exchanges defined, exiting... <<<")
        os._exit(0)

    # bootstrap ORM
    execute_from_command_line([sys.argv[0], 'makemigrations'])
    execute_from_command_line([sys.argv[0], 'migrate'])
    django.setup()

    # development mode
    if not CONFIG["General"]["production"]:
        logger.info(">>> DEVELOPMENT MODE, NO SCHEDULING <<<")
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