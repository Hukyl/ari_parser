from telebot import TeleBot

import settings

from models.user import Updates
from models.chat import Chat


bot = TeleBot(settings.BOT_TOKEN, parse_mode='html')


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
    for chat in Chat.get_subscribed():
        message = (
            f"<b>Email</b>: {updates.owner.email}\n"
            f"<b>{data['attr'].title()}</b>: {getattr(updates, data['attr'])}"
        )
        if data.get('image'):
            bot.send_photo(chat.id, data['image'], message)
        else:
            bot.send_message(chat.id, message)


if __name__ == '__main__':
    bot.infinite_polling()
