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

import time
import yaml
import logging
import requests as req

from wrapt import synchronized

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.getLogger('requests.packages.urllib3').setLevel(logging.INFO)
logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)

ticks = {
     '5m': 5,
    '30m': 30,
     '1h': 60,
     '4h': 60*4,
     '1d': 60*24
}


#
#
#
def generate_nonce():
    return int(time.time()*10)


#
#
#
def get_btc_usd():
    url = "https://api.coindesk.com/v1/bpi/currentprice.json"
    r = req.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    })
    data = r.json()

    if not data["bpi"]:
        raise RuntimeError("coindesk: {}".format(data))

    return data['bpi']['USD']['rate_float']


#
#
#
@synchronized
def get_conf(filename="config.yml"):
    _cur_conf = None

    with open(filename) as file:
        _cur_conf = yaml.load(file)

    logger.debug("config loaded")

    return _cur_conf




