from random import choice, sample
import subprocess
from time import sleep
import threading

from models.driver import Driver
from models.page import HomePage
from models.user import User
from models.logger import DefaultLogger
from models import exceptions
import bot
import settings
from utils import cycle


logger = DefaultLogger()


def create_user(user_data: dict[str, str]):
    if not User.exists(user_data['email']):
        User.create_user(user_data['email'], user_data['password'])
    user = User(user_data['email'])
    user.password = user_data['password']
    return user


@bot.notify_errors
@logger.catch_error
def thread_checker(user: dict[str, str]):
    user = create_user(user)
    driver = Driver(user)
    user.updates.add_observer(bot.send_updates)
    proxies = cycle([''] if not settings.PROXIES else sample(
        settings.PROXIES, len(settings.PROXIES)
    ))
    page = HomePage(driver)
    driver.get(page.URL)
    page.change_language('en')
    if user.session:
        driver.add_cookie({
            'name': settings.SESSION_COOKIE_NAME, 
            'value': user.session, 'domain': page.URL.domain
        })
    while True:
        driver.set_proxy(next(proxies))
        try:
            driver.safe_get(page.URL)
        except exceptions.AuthorizationException as e:
            logger.log(e.args[0], to_stdout=True)
            bot.send_error(driver.user.email, e)
            return
        if page.status != user.updates.status:
            user.updates.update(
                'status', page.status, image=page.status_screenshot
            )
            driver.save_snapshot(settings.SNAPSHOTS_PATH)
        sleep(choice(settings.REQUEST_TIMEOUT))


if __name__ == '__main__':
    threads = [
        threading.Thread(
            target=thread_checker, args=(user, ), daemon=True
        ) for user in settings.USERS
    ]
    for thread in threads:
        thread.start()
    print("Parser started")
    bot.bot.infinity_polling()
    print("Shutting down the parser")
    # Kill all instances of driver
    subprocess.call(
        settings.ChromeData.TASK_KILL_COMMAND, 
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
