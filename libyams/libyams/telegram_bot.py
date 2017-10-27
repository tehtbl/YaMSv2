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

from telegram.error import NetworkError
from telegram.ext import CommandHandler, Updater
from telegram import ParseMode, Bot, Update
from wrapt import synchronized

from cfg import get_conf

# Remove noisy log messages
logging.getLogger('requests.packages.urllib3').setLevel(logging.INFO)
logging.getLogger('telegram').setLevel(logging.INFO)
logger = logging.getLogger(__name__)

_updater = None

conf = get_conf()


def authorized_only(command_handler):
    """
    Decorator to check if the message comes from the correct chat_id
    :param command_handler: Telegram CommandHandler
    :return: decorated function
    """

    def wrapper(*args, **kwargs):
        bot, update = args[0], args[1]
        if not isinstance(bot, Bot) or not isinstance(update, Update):
            raise ValueError('Received invalid Arguments: {}'.format(*args))

        chat_id = int(conf['telegram']['chat_id'])
        if int(update.message.chat_id) == chat_id:
            logger.info('Executing handler: %s for chat_id: %s', command_handler.__name__, chat_id)
            return command_handler(*args, **kwargs)
        else:
            logger.info('Rejected unauthorized message from: %s', update.message.chat_id)

    return wrapper


class TelegramHandler(object):
    @staticmethod
    @authorized_only
    def _status(bot, update):
        """
        Handler for /status.
        Returns the current TradeThread status
        :param bot: telegram bot
        :param update: message update
        :return: None
        """

        TelegramHandler.send_msg('*Status:* `status method`', bot=bot)

    @staticmethod
    @authorized_only
    def _start(bot, update):
        """
        Handler for /start.
        Starts TradeThread
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        TelegramHandler.send_msg('*Status:* `start method`', bot=bot)

    @staticmethod
    @authorized_only
    def _stop(bot, update):
        """
        Handler for /stop.
        Stops TradeThread
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        TelegramHandler.send_msg('*Status:* `stop method`', bot=bot)

    @staticmethod
    @synchronized
    def get_updater(config):
        """
        Returns the current telegram updater or instantiates a new one
        :param config: dict
        :return: telegram.ext.Updater
        """
        global _updater
        if not _updater:
            _updater = Updater(token=config['telegram']['token'], workers=0)
        return _updater

    @staticmethod
    def listen():
        """
        Registers all known command handlers and starts polling for message updates
        :return: None
        """
        # Register command handler and start telegram message polling
        handles = [
            CommandHandler('status', TelegramHandler._status),
            CommandHandler('start', TelegramHandler._start),
            CommandHandler('stop', TelegramHandler._stop),
        ]

        for handle in handles:
            TelegramHandler.get_updater(conf).dispatcher.add_handler(handle)

        TelegramHandler.get_updater(conf).start_polling(
            clean=True,
            bootstrap_retries=3,
            timeout=30,
            read_latency=60,
        )
        logger.info('TelegramHandler is listening for following commands: {}'.format([h.command for h in handles]))

    @staticmethod
    def send_msg(msg, bot=None, parse_mode=ParseMode.MARKDOWN):
        """
        Send given markdown message
        :param msg: message
        :param bot: alternative bot
        :param parse_mode: telegram parse mode
        :return: None
        """
        if conf['telegram'].get('enabled', False):
            try:
                bot = bot or TelegramHandler.get_updater(conf).bot
                try:
                    bot.send_message(conf['telegram']['chat_id'], msg, parse_mode=parse_mode)
                except NetworkError as error:
                    # Sometimes the telegram server resets the current connection,
                    # if this is the case we send the message again.
                    logger.warning('Got Telegram NetworkError: %s! Trying one more time.', error.message)
                    bot.send_message(conf['telegram']['chat_id'], msg, parse_mode=parse_mode)
            except Exception:
                logger.exception('Exception occurred within Telegram API')
