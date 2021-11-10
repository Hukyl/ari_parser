import logging
from typing import Any

from telebot import TeleBot, logger as telebot_logger
from telebot.types import Message
from loguru import logger

import settings
from models import Observer, Observable
from models.chat import Chat

telebot_logger.setLevel(logging.FATAL)

_bot = TeleBot(settings.BOT_TOKEN, parse_mode='html')


class Bot(Observer):
    @_bot.message_handler(commands=['start'])
    @staticmethod
    def greet(msg: Message) -> None:
        _bot.send_message(
            msg.chat.id, f"Hello, {msg.from_user.first_name}!"
        )

    @_bot.message_handler(commands=['help'])
    @staticmethod
    def send_help(msg: Message) -> None:
        _bot.send_message(
            msg.chat.id, 
            "/subscribe - subscribe to updates\n/unsubscribe - unsubscribe"
        )

    @_bot.message_handler(commands=['subscribe'])
    @staticmethod
    def subscribe(msg: Message) -> None:
        chat = Chat(msg.chat.id)
        if chat.is_subscribed:
            _bot.reply_to(msg, "You are already subscribed!")
        else:
            chat.subscribe()
            _bot.reply_to(msg, "You have subscribed!")

    @_bot.message_handler(commands=['unsubscribe'])
    @staticmethod
    def unsubscribe(msg: Message) -> None:
        chat = Chat(msg.chat.id)
        if not chat.is_subscribed:
            _bot.reply_to(msg, "You are already unsubscribed!")
        else:
            chat.unsubscribe()
            _bot.reply_to(msg, "You have unsubscribed!")

    def update(
                self, observable: Observable, attrs: dict[str, Any],
                *, additional: dict[str, Any]
            ) -> None:
        message = [f"<b>Email</b>: {additional['email']}"]
        if name := additional.get('dependent_name'):
            message.append(f'<b>Applicant name</b>: {name}')
        for k in sorted(attrs):
            message.append(f"<b>{k.replace('_', ' ').title()}</b>: {attrs[k]}")
        else:
            message = '\n'.join(message)
        for chat in Chat.get_subscribed():
            if additional.get('image'):
                _bot.send_photo(chat.id, additional['image'], message)
            else:
                _bot.send_message(chat.id, message)

    @staticmethod
    def send_message(email: str, message: str) -> None:
        message = f"<b>Email</b>: {email}\n<b>Message</b>: {message}"
        for chat in Chat.get_subscribed():
            _bot.send_message(chat.id, message)

    @staticmethod
    def send_error(email: str, message: str) -> None:
        message = (
            f'<b>Error</b>\n<b>Email</b>: {email}\n<b>Message</b>: {message}'
        )
        for chat in Chat.get_subscribed():
            _bot.send_message(chat.id, message)

    @staticmethod
    def infinity_polling() -> None:
        logger.info('Bot started', email='\b')
        _bot.infinity_polling()
        logger.info('Bot stopped', email='\b')


def main():
    bot = Bot()
    bot.infinity_polling()


if __name__ == '__main__':
    main()
