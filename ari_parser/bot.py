from telebot import TeleBot

import settings

from models.user import Updates
from models.chat import Chat


bot = TeleBot(settings.BOT_TOKEN)


@bot.message_handler(commands=['start'])
def greet(msg):
    bot.send_message(msg.chat.id, f"Hello, {msg.from_user.first_name}!")


@bot.message_handler(commands=['help'])
def send_help(msg):
    bot.send_message(
        msg.chat.id, 
        "/subscribe - subscribe to updates\n/unsubscribe - unsubscribe"
    )


def send_updates(updates: Updates, data: dict):
    for chat in Chat.get_subscribed():
        message = (
            f"**Email**: {updates.owner.email}\n"
            f"**{data['attr'].title()}**: {getattr(updates, data['attr'])}"
        )
        if data.get('image'):
            bot.send_photo(chat.id, data['image'], message)
        else:
            bot.send_message(chat.id, message)


if __name__ == '__main__':
    bot.infinite_polling()
