from time import sleep
import threading
from functools import wraps

from models.driver import Driver
from models.page import LoginPage, HomePage
from models.user import User
from models.logger import Logger
from . import bot
import settings


logger = Logger()


def create_user(user: dict[str, str]):
    if not User.exists(user['email']):
        User.create_user(user['email'], user['password'])
    return User(user['email'])


def create_driver(user: User):
    return Driver(user)


def thread_checker(user: dict[str, str]):
    ...


if __name__ == '__main__':
    for user in settings.USERS:
        threading.Thread(target=thread_checker, args=(user, )).start()
    try:
        while True:
            sleep(1000000)
    except KeyboardInterrupt:
        print("Shutting down the parser")
