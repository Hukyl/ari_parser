import logging

from telebot import TeleBot, logger

import settings
from models.chat import Chat
from models import Observer, Observable


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
    def update(observable: Observable, attrs: dict, *, additional: dict):
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

    def infinity_polling(self):
        _bot.infinity_polling()


def main():
    bot = Bot()
    bot.infinity_polling()


if __name__ == '__main__':
    main()
