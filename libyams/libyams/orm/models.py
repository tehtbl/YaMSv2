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

from django.db import models


#
# TickerData
#
class TickerData(models.Model):

    xchg = models.CharField(db_index=True, max_length=255, verbose_name="Exchange")
    pair = models.CharField(db_index=True, max_length=10, verbose_name="Pair")
    tick = models.CharField(db_index=True, max_length=4, verbose_name="Tick Length")

    tval = models.DateTimeField(db_index=True, verbose_name="received_timeval")

    open = models.FloatField(default=0.0, verbose_name="open")
    high = models.FloatField(default=0, verbose_name="high")
    low = models.FloatField(default=0, verbose_name="low")
    close = models.FloatField(default=0, verbose_name="close")

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TickerData"
        verbose_name_plural = verbose_name
        unique_together = ('xchg', 'pair', 'tick', 'tval')

    def __str__(self):
        return u'exchange(%s), pair(%s), time(%s), close(%s)' % (self.xchg, self.pair, self.tval, self.close)

    def __unicode__(self):
        return self.__str__()


#
# Indicator
#
class Indicator(models.Model):

    name = models.CharField(max_length=80, verbose_name="Indicator Name", db_index=True)
    value = models.CharField(max_length=80, verbose_name="Indicator Value")

    data = models.ForeignKey(TickerData, related_name="indicator_tickerdata", db_index=True)

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Indicator"
        verbose_name_plural = verbose_name + "s"

    def __str__(self):
        return u'%s' % self.name

    def __unicode__(self):
        return self.__str__()
