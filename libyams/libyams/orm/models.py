# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid as uuid

from django.db import models

CH_Ticks = (
    ('1', '1m'),
    ('2', '5m'),
    ('3', '30'),
    ('4', '1h'),
    ('5', '4h'),
    ('6', '1d'),
    ('7', '1m'),
)

CH_Signal = (
    ('1', 'none'),
    ('2', 'buy'),
    ('3', 'sell'),
)

CH_SignalStrength = (
    ('1', 'none'),
    ('2', 'weak'),
    ('3', 'normal'),
    ('4', 'strong'),
)


#
# CurrencyPair
#
class CurrencyPair(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    cur_base = models.CharField(max_length=4, verbose_name="Base Currency", default="BTC")
    cur_name = models.CharField(max_length=4, verbose_name="Target Currency")

    tick_len = models.CharField(max_length=1, choices=CH_Ticks, default='6', verbose_name="Tick Length")

    open = models.PositiveIntegerField(default=0, verbose_name="open")
    high = models.PositiveIntegerField(default=0, verbose_name="high")
    low = models.PositiveIntegerField(default=0, verbose_name="low")
    close = models.PositiveIntegerField(default=0, verbose_name="close")
    time_val = models.DateTimeField(unique=True, verbose_name="received_timeval")

    indicator = models.ForeignKey('Indicator', related_name="curpair_indicator")

    class Meta:
        verbose_name = "CurrencyPair"
        verbose_name_plural = verbose_name + "s"

    def __str__(self):
        return u'%s' % self.cur_name

    def __unicode__(self):
        return self.__str__()

#
# TODO: how to combind indicator and timevalue?
#


#
# Indicator
#
class Indicator(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=80, verbose_name="Indicator Name")
    value = models.CharField(max_length=80, verbose_name="Indicator Name")

    signal = models.CharField(max_length=1, choices=CH_Signal, default='1', verbose_name="Signal")
    signal_strength = models.CharField(max_length=1, choices=CH_SignalStrength, default='1',
                                       verbose_name="Signal Strength")

    class Meta:
        verbose_name = "Indicator"
        verbose_name_plural = verbose_name + "s"

    def __str__(self):
        return u'%s' % self.name

    def __unicode__(self):
        return self.__str__()


#
# Settings
#
class Settings(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    base_currency = models.CharField(max_length=4, verbose_name="Base Currency")

    class Meta:
        verbose_name = "Settings"
        verbose_name_plural = verbose_name

    def __str__(self):
        return u'%s' % self.uuid

    def __unicode__(self):
        return self.__str__()
