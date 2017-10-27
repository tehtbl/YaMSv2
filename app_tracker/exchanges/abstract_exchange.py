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

from abc import ABCMeta, abstractmethod, abstractproperty


class AbstractExchange(object):
    __metaclass__ = ABCMeta

    def __init__(self, config):
        self.config = config

    @property
    def name(self):
        """
        returns name of class

        :return:
        """
        return self.__class__.__name__

    @abstractmethod
    def get_markets(self):
        """

        :return: returns all possible markets
        """

    @abstractmethod
    def get_ticker_data(self, pair, tick):
        """
        returns all ticker data for a given pair and interval

        :param pair: pair for the market
        :param tick: interval to search for
        :return: json encoded list of list of ohcl data
        """