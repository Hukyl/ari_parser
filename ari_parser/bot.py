from time import sleep
import logging

from telebot import TeleBot, logger

import settings
from models.account import Updates
from models.chat import Chat
from models import Observer


logger.setLevel(logging.FATAL)

_bot = TeleBot(settings.BOT_TOKEN, parse_mode='html')


class Bot(Observer):
    @_bot.message_handler(commands=['start'])
    def greet(msg):
        _bot.send_message(
            msg.chat.id, f"Hello, {msg.from_user.first_name}!"
        )

    @_bot.message_handler(commands=['help'])
    def send_help(msg):
        _bot.send_message(
            msg.chat.id, 
            "/subscribe - subscribe to updates\n/unsubscribe - unsubscribe"
        )

    @_bot.message_handler(commands=['subscribe'])
    def subscribe(msg):
        chat = Chat(msg.chat.id)
        if chat.is_subscribed:
            _bot.reply_to(msg, "You are already subscribed!")
        else:
            chat.subscribe()
            _bot.reply_to(msg, "You have subscribed!")

    @_bot.message_handler(commands=['unsubscribe'])
    def unsubscribe(msg):
        chat = Chat(msg.chat.id)
        if not chat.is_subscribed:
            _bot.reply_to(msg, "You are already unsubscribed!")
        else:
            chat.unsubscribe()
            _bot.reply_to(msg, "You have unsubscribed!")

    @staticmethod
    def update(observable: Updates, attrs: dict, *, additional: dict):
        message = [f"<b>Email</b>: {observable.owner.email}"]
        for k, v in attrs.items():
            message.append(f"<b>{k.replace('_', '').title()}</b>: {v}")
        else:
            message = '\n'.join(message)
        for chat in Chat.get_subscribed():
            if additional.get('image'):
                _bot.send_photo(chat.id, additional['image'], message)
            else:
                _bot.send_message(chat.id, message)

    @staticmethod
    def send_message(email: str, message: str):
        message = f"<b>Email</b>: {email}\n<b>Message</b>: {message}"
        for chat in Chat.get_subscribed():
            _bot.send_message(chat.id, message)

    @staticmethod
    def send_error(email:str, message: str):
        message = (
            f'<b>Error</b>\n<b>Email</b>: {email}\n<b>Message</b>: {message}'
        )
        for chat in Chat.get_subscribed():
            _bot.send_message(chat.id, message)

    @staticmethod
    def notify_errors(func):
        def inner(driver, *args, **kwargs):
            if func(driver, *args, **kwargs) is True:
                return
            Bot.send_error(driver.account.email, 'crawler error')
            sleep(30 * 60)
            if func(driver, *args, **kwargs) is True:
                return
            Bot.send_error(driver.account.email, 'crawler error')
        return inner

    def infinity_polling(self):
        _bot.infinity_polling()


def main():
    bot = Bot()
    bot.infinity_polling()


if __name__ == '__main__':
    main()
