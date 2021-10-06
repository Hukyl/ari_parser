from time import sleep
import logging

from telebot import TeleBot, logger

import settings
from models.user import Updates
from models.chat import Chat


bot = TeleBot(settings.BOT_TOKEN, parse_mode='html')
logger.setLevel(logging.FATAL)


@bot.message_handler(commands=['start'])
def greet(msg):
    bot.send_message(msg.chat.id, f"Hello, {msg.from_user.first_name}!")


@bot.message_handler(commands=['help'])
def send_help(msg):
    bot.send_message(
        msg.chat.id, 
        "/subscribe - subscribe to updates\n/unsubscribe - unsubscribe"
    )


@bot.message_handler(commands=['subscribe'])
def subscribe(msg):
    chat = Chat(msg.chat.id)
    if chat.is_subscribed:
        bot.reply_to(msg, "You are already subscribed!")
    else:
        chat.subscribe()
        bot.reply_to(msg, "You have subscribed!")


@bot.message_handler(commands=['unsubscribe'])
def unsubscribe(msg):
    chat = Chat(msg.chat.id)
    if not chat.is_subscribed:
        bot.reply_to(msg, "You are already unsubscribed!")
    else:
        chat.unsubscribe()
        bot.reply_to(msg, "You have unsubscribed!")


def send_updates(updates: Updates, data: dict):
    message = (
        f"<b>Email</b>: {updates.owner.email}\n"
        f"<b>{data['attr'].title()}</b>: {getattr(updates, data['attr'])}"
    )    
    for chat in Chat.get_subscribed():
        if data.get('image'):
            bot.send_photo(chat.id, data['image'], message)
        else:
            bot.send_message(chat.id, message)


def send_message(email: str, message: str):
    message = f"<b>Email</b>: {email}\n<b>Message</b>: {message}"
    for chat in Chat.get_subscribed():
        bot.send_message(chat.id, message)


def send_error(email:str, message: str):
    message = (
        f'<b>Error</b>\n<b>Email</b>: {email}\n<b>Message</b>: {message}'
    )    
    for chat in Chat.get_subscribed():
        bot.send_message(chat.id, message)



def notify_errors(func):
    def inner(user: dict[str, str]):
        message = (
            f"<b>Error</b>\n<b>Email</b>: {user['email']}\n"
            "<b>Reason</b>: crawler error"
        )
        func(user)
        for chat in Chat.get_subscribed():
            bot.send_message(chat.id, message)
        sleep(30 * 60)
        func(user)
        for chat in Chat.get_subscribed():
            bot.send_message(chat.id, message)
    return inner


if __name__ == '__main__':
    bot.infinite_polling()
