from datetime import datetime
from random import choice, sample
import subprocess
from time import sleep
import threading

from models.driver import Driver
from models.page import (
    HomePage, MainAppointmentPage, DependentAppointmentPage, 
    ApplicantsPage, BasePage
)
from models.account import Account
from models.logger import DefaultLogger
from models import exceptions
from bot import Bot
import settings
from utils import cycle, cleared


logger = DefaultLogger()
proxies = cycle([''] if not settings.PROXIES else sample(
    settings.PROXIES, len(settings.PROXIES)
))
bot = Bot()


def create_account(account_data: dict[str, str]):
    if not Account.exists(account_data['email']):
        Account.create_account(account_data['email'], account_data['password'])
    account = Account(account_data['email'])
    account.password = account_data['password']
    return account


def schedule(driver: Driver, page: BasePage):
    pass


@logger.catch_error
def thread_checker(account: dict[str, str], applicants: list[str]):
    account = create_account(account)
    for applicant in applicants:
        account.add_dependent(applicant)
    driver = Driver(account)
    account.updates.add_observer(bot)
    page = HomePage(driver)
    driver.get(page.URL)
    page.change_language('en')
    try:
        driver.log_in()
    except exceptions.AuthorizationException as e:
        logger.log(e.args[0], to_stdout=True)
        bot.send_error(driver.account.email, e)
        return
    if account.auth_token:
        driver.add_cookie({
            'name': settings.AUTH_TOKEN_COOKIE_NAME, 
            'value': account.auth_token, 'domain': page.URL.domain
        })
        logger.log(f"{account.email}: an auth token cookie is used")
    if account.session_id:
        driver.add_cookie({
            'name': settings.SESSION_ID_COOKIE_NAME, 
            'value': account.session_id, 'domain': page.URL.domain
        })
        logger.log(f"{account.email}: a session id cookie is used")      
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
    account = driver.account
    while True:
        with cleared(event):
            driver.switch_to_tab(-1)
            with threading.Lock():
                driver.set_proxy(next(proxies))
            logger.log(f'{account.email}: checking status')
            driver.safe_get(page.URL)
            if page.status != account.updates.status:
                logger.log(f"{account.email}: status changed")
                account.updates.update(
                    {'status': page.status}, 
                    additional={'image': page.status_screenshot}
                )
                driver.save_snapshot(settings.SNAPSHOTS_PATH)
            else:
                logger.log(f"{account.email}: status has not changed")
            sleep(3)
        sleep(choice(settings.RequestTimeout.STATUS))


@bot.notify_errors
@logger.catch_error
def check_appointment(driver: Driver, event: threading.Event):
    page = HomePage(driver)
    with cleared(event):
        driver.switch_to_tab(0)
        page.click_calendar()
    page = MainAppointmentPage(driver)
    account = driver.account
    while True:
        with cleared(event):
            driver.switch_to_tab(0)
            with threading.Lock():
                driver.set_proxy(next(proxies))
            logger.log(f'{account.email}: checking appointments')
            driver.safe_get(page.URL)
            page.matter_option = 'ARI'
            options = page.branch_options
            options = list(filter(
                lambda x: (
                    x not in settings.AppointmentData.BLOCKED_OFFICES
                ), options
            ))
            if options:
                logger.log(
                    f'{account.email}: new appointment branches have appeared'
                )
                if not account.is_signed:
                    data = page.schedule_main(options)
                    account.updates.update({
                        'office_signed': data['office'], 
                        'datetime_signed': data['date']
                    })
                for dep in sorted(account.dependents, key=lambda x: x.id):
                    if not dep.is_signed:
                        driver.open_new_tab()
                        p = HomePage(driver)
                        driver.get(p.URL)
                        p.click_applicants()
                        p = ApplicantsPage(driver)
                        p.set_applicant(dep.name)
                        p.get_applicant_appointment()
                        p = DependentAppointmentPage(driver)
                        p.matter_option = 'ARI'
                        p.schedule(
                            options, account.updates.datetime_signed, 
                            account.updates.office_signed, 
                            settings.AppointmentData.HOUR_OFFICE_OFFSET
                        )
                        dep.is_signed = True
            sleep(3)
        sleep(choice(settings.RequestTimeout.APPOINTMENT))



if __name__ == '__main__':
    threads = [
        threading.Thread(
            target=thread_checker, args=(account.to_dict(), applicants), 
            daemon=True
        ) for account, applicants in settings.ACCOUNTS.items()
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
