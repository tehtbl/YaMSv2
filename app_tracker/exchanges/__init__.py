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

import logging

from libyams.utils import get_conf
from bittrex import Bittrex
from bitfinex import Bitfinex

logger = logging.getLogger(__name__)

CONFIG = get_conf()

Exchanges = {
    'BITTREX': Bittrex,
    'BITFINEX': Bitfinex,
}


#
#
#
def get_exchange_obj(str):

    if str in CONFIG["DataTracker"]["exchanges"]:
        try:
            return Exchanges[str.upper()](CONFIG)
        except KeyError:
            raise RuntimeError('Exchange {} is not supported'.format(str))

    return None
