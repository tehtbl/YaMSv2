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


class BittrexExchange(AbstractExchange):

    def __init__(self, cfg):
        super(BittrexExchange, self).__init__(cfg)

    def get_ticker_data(self, pair, tick):
        return []

    #
    #
    #
    def get_market_summary(self):
        url = "https://bittrex.com/api/v2.0/pub/Markets/GetMarketSummaries"
        r = req.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        })
        data = r.json()
        if not data["success"]:
            raise RuntimeError("BITTREX: {}".format(data["message"]))
        return data['result']

    #
    #
    #
    def get_related_currencies(self):
        rel_curr = []
        btc_usd_price = get_btc_usd()

        # filter out related currencies
        for c in get_market_summary():
            if c['Market']['MarketName'] not in CONFIG["bittrex"]["blacklist"]:
                val = c['Summary']['Last'] * btc_usd_price
                if CONFIG["bittrex"]["min_price_usd"] < val < CONFIG["bittrex"]["max_price_usd"]:
                    if CONFIG["bittrex"]["stake_currency_enabled"]:
                        if c['Market']['BaseCurrency'] == CONFIG["bittrex"]["stake_currency"]:
                            rel_curr.append(c)
                    else:
                        rel_curr.append(c)

        # save index
        with open(os.path.join("/data", "__INDEX__.json"), 'w') as outfile:
            json.dump([c['Market']['MarketName'] for c in rel_curr], outfile, indent=2)
            outfile.close()

        return rel_curr



    #
    # get data from BITTREX ticker, possible tick values are: onemin, thirtymin, hour, daily, weekly
    #
    def btrx_get_ticker(self, pair, tick='daily'):
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
