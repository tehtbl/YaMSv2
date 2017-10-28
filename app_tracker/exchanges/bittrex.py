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

import requests as req

from abstract_exchange import AbstractExchange


class Bittrex(AbstractExchange):

    #
    # init
    #
    def __init__(self, cfg):
        super(Bittrex, self).__init__(cfg)
        self.tick_dict = {
            '5m': 'fivemin',
            '30m': 'thirtymin',
            '1h': 'hour', # we have no 4h on bittrex o_O :(
            '1d': 'daily'
        }

    #
    # get available markets
    #
    def get_markets(self):
        url = "https://bittrex.com/api/v2.0/pub/Markets/GetMarketSummaries"
        r = req.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        })
        data = r.json()
        if not data["success"]:
            raise RuntimeError("BITTREX: {}".format(data["message"]))

        return map(lambda x: x['Summary']['MarketName'], data['result'])

    #
    # get data from BITTREX ticker
    #
    def get_ticker_data(self, pair, tick):

        if tick not in self.tick_dict.keys():
            raise RuntimeError('unknown tick %s for bittrex' % (tick))

        url = 'https://bittrex.com/Api/v2.0/pub/market/GetTicks'
        params = {
            'marketName': pair,
            'tickInterval': self.tick_dict[tick],
        }

        r = req.get(url, params=params, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        })

        data = r.json()
        if not data['success']:
            raise RuntimeError('BITTREX: {}'.format(data['message']))

        return data['result']

    # #
    # # update labels
    # #
    # def parse_ticker_dataframe(self, data):
    #     from pandas import DataFrame
    #
    #     df = DataFrame(data) \
    #         .drop('BV', 1) \
    #         .rename(columns={'C': 'close', 'V': 'volume', 'O': 'open', 'H': 'high', 'L': 'low', 'T': 'date'}) \
    #         .sort_values('date')
    #
    #     return df
