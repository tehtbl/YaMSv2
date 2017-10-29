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

    def __init__(self, cfg, q):
        self.config = cfg
        self.sender_q = q

    @property
    def name(self):
        """
        returns name of class

        :return:
        """
        return self.__class__.__name__

    @abstractmethod
    def start_receiver(self):
        """
        start the exchange receiver, which gets all ticker data and pushes ist into a queue

        :return: dict of data
        Example:
            {
                'exchange': self.name,
                'market': 'BTC-XVG'
                'tick': '5m'
                'data': [
                    {
                        'open': ...
                        'close': ...
                        'high': ...
                        'low': ...
                        'timestamp': ...
                    }
                ]
            }
        """
