from random import choice, sample
import subprocess
from time import sleep
import threading

from models.driver import Driver
from models.page import HomePage, AppointmentPage
from models.user import User
from models.logger import DefaultLogger
from models import exceptions
import bot
import settings
from utils import cycle


logger = DefaultLogger()
proxies = cycle([''] if not settings.PROXIES else sample(
    settings.PROXIES, len(settings.PROXIES)
))


def create_user(user_data: dict[str, str]):
    if not User.exists(user_data['email']):
        User.create_user(user_data['email'], user_data['password'])
    user = User(user_data['email'])
    user.password = user_data['password']
    return user


@logger.catch_error
def thread_checker(user: dict[str, str]):
    user = create_user(user)
    driver = Driver(user)
    user.updates.add_observer(bot.send_updates)
    page = HomePage(driver)
    driver.get(page.URL)
    page.change_language('en')
    if user.auth_token:
        driver.add_cookie({
            'name': settings.AUTH_TOKEN_COOKIE_NAME, 
            'value': user.auth_token, 'domain': page.URL.domain
        })
        logger.log(f"{user.email}: an auth token cookie is used")
    if user.session_id:
        driver.add_cookie({
            'name': settings.SESSION_ID_COOKIE_NAME, 
            'value': user.session_id, 'domain': page.URL.domain
        })
        logger.log(f"{user.email}: a session id cookie is used")      
    event = threading.Event()
    event.set()
    driver.open_new_tab()
    driver.switch_to_tab(0)
    for func in [check_status, check_appointment]:
        threading.Thread(
            target=func, args=(driver, event), daemon=True
        ).start()
    return


@bot.notify_errors
@logger.catch_error
def check_status(driver: Driver, event: threading.Event):
    page = HomePage(driver)
    user = driver.user
    while True:
        event.wait()
        event.clear()
        driver.switch_to_tab(-1)
        with threading.Lock():
            driver.set_proxy(next(proxies))
        logger.log(f'{user.email}: checking status')
        try:
            driver.safe_get(page.URL)
        except exceptions.AuthorizationException as e:
            logger.log(e.args[0], to_stdout=True)
            bot.send_error(driver.user.email, e)
            return
        if page.status != user.updates.status:
            logger.log(f"{user.email}: status changed")
            user.updates.update(
                'status', page.status, image=page.status_screenshot
            )
            driver.save_snapshot(settings.SNAPSHOTS_PATH)
        else:
            logger.log(f"{user.email}: status has not changed")
        sleep(3)
        event.set()
        sleep(choice(settings.RequestTimeout.STATUS))


@bot.notify_errors
@logger.catch_error
def check_appointment(driver: Driver, event: threading.Event):
    page = AppointmentPage(driver)
    user = driver.user
    while True:
        event.wait()
        event.clear()
        driver.switch_to_tab(0)
        with threading.Lock():
            driver.set_proxy(next(proxies))
        logger.log(f'{user.email}: checking appointments')
        try:
            driver.safe_get(page.URL)
        except exceptions.AuthorizationException as e:
            logger.log(e.args[0], to_stdout=True)
            bot.send_error(driver.user.email, e)
            return
        page.matter_option = 'ARI'
        options = page.branch_options
        options = list(filter(
            lambda x: (
                x not in settings.AppointmentData.BLOCKED_OFFICES
            ), options
        ))
        if options:
            bot.send_message(
                user.email, 'new appointment branches have appeared'
            )
        sleep(3)
        event.set()
        sleep(choice(settings.RequestTimeout.APPOINTMENT))



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
        settings.ChromeData.TASK_KILL_COMMAND.split(), 
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
