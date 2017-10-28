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

from __future__ import unicode_literals

import uuid as uuid
from django.db import models

# CH_Ticks = (
#     ('1', '1m'),
#     ('2', '5m'),
#     ('3', '30'),
#     ('4', '1h'),
#     ('5', '4h'),
#     ('6', '1d'),
#     ('7', '1m'),
# )
#
# CH_Signal = (
#     ('1', 'none'),
#     ('2', 'buy'),
#     ('3', 'sell'),
# )
#
# CH_SignalStrength = (
#     ('1', 'none'),
#     ('2', 'weak'),
#     ('3', 'normal'),
#     ('4', 'strong'),
# )


#
# Market
#
class Market(models.Model):
    # uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    exchange = models.CharField(max_length=255, verbose_name="Exchange")
    pair = models.CharField(max_length=10, verbose_name="Pair")

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Market"
        verbose_name_plural = verbose_name + "s"

    def __str__(self):
        return u'%s --- %s' % (self.exchange, self.pair)

    def __unicode__(self):
        return self.__str__()


#
# TickerData
#
class TickerData(models.Model):
    # uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    market = models.ForeignKey(Market, related_name="tickerdata_market")
    tick_len = models.CharField(max_length=4, verbose_name="Tick Length")
    time_val = models.DateTimeField(verbose_name="received_timeval")

    open = models.PositiveIntegerField(default=0, verbose_name="open")
    high = models.PositiveIntegerField(default=0, verbose_name="high")
    low = models.PositiveIntegerField(default=0, verbose_name="low")
    close = models.PositiveIntegerField(default=0, verbose_name="close")

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TickerData"
        verbose_name_plural = verbose_name
        unique_together = ('market', 'tick_len', 'time_val', 'open', 'high', 'low', 'close')

    def __str__(self):
        return u'market(%s), time(%s), close(%s)' % (self.market, self.time_val, self.close)

    def __unicode__(self):
        return self.__str__()


#
# Indicator
#
class Indicator(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=80, verbose_name="Indicator Name")
    value = models.CharField(max_length=80, verbose_name="Indicator Name")

    class Meta:
        verbose_name = "Indicator"
        verbose_name_plural = verbose_name + "s"

    def __str__(self):
        return u'%s' % self.name

    def __unicode__(self):
        return self.__str__()
