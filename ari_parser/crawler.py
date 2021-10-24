import random
import subprocess
from time import sleep
import threading
from datetime import datetime, timedelta

from selenium.common import exceptions as selenium_exceptions

from models.driver import Driver
from models.page import HomePage, AppointmentPage, ApplicantsPage
from models.account import Account
from models.logger import DefaultLogger
from models import exceptions
from bot import Bot
import settings
from utils import cycle, cleared, FrozenDict


logger = DefaultLogger()
proxies = cycle([''] if not settings.PROXIES else random.sample(
    settings.PROXIES, len(settings.PROXIES)
))
bot = Bot()


def create_account(account_data: FrozenDict, data: list[str]):
    if not Account.exists(email=account_data['email']):
        Account.create_account(account_data['email'], account_data['password'])
    account = Account(account_data['email'])
    account.password = account_data['password']
    account.updates.day_offset = data['day_offset']
    for name in data['dependents']:
        account.add_dependent(name)
    return account


@bot.notify_errors
@logger.catch_error
def thread_checker(account: dict[str, str], data: dict):
    account = create_account(account, data)
    driver = Driver(account)
    account.updates.add_observer(bot)
    page = HomePage(driver)
    page.get()
    page.language = 'en'
    try:
        driver.log_in()
    except exceptions.AuthorizationException as e:
        logger.log(e.args[0], to_stdout=True)
        bot.send_error(driver.account.email, e)
        return
    if account.auth_token:
        driver.add_cookie({
            'name': settings.AUTH_TOKEN_COOKIE_NAME, 
            'value': account.auth_token,
        })
        logger.log(f"{account.email}: an auth token cookie is used")
    if account.session_id:
        driver.add_cookie({
            'name': settings.SESSION_ID_COOKIE_NAME, 
            'value': account.session_id,
        })
        logger.log(f"{account.email}: a session id cookie is used")      
    event = threading.Event()
    event.set()
    driver.open_new_tab()
    driver.switch_to_tab(0)
    for dependent in account.dependents:
        driver.open_new_tab()
        p = HomePage(driver)
        p.get()
        p.language = 'en'
        p.click_applicants()
        p = ApplicantsPage(driver)
        p.set_applicant(dependent.name)
        p.get_applicant_appointment()
        sleep(2)
    else:     
        driver.switch_to_tab(0)
    for check in data['checks']:
        threading.Thread(
            target=globals()[f'check_{check}'], args=(driver, event), 
            daemon=True
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
        sleep(random.choice(settings.RequestTimeout.STATUS))


def filter_available_meetings(meetings: dict, account: Account) -> dict:
    min_datetime = (datetime.now() + timedelta(
        days=account.updates.day_offset
    )).date()
    meetings = list(filter(
        lambda x: (
            x['office'] not in settings.AppointmentData.BLOCKED_OFFICES
        ), meetings
    ))  # filter out inappropriate offices
    meetings = list(filter(
        lambda x: x['datetime'].date() >= min_datetime, meetings
    ))  # filter offices that are too close to the present dateetime
    if not account.is_signed:
        if len(meetings) >= (
                settings.AppointmentData.NUMBER_TO_INCREASE_DAY_OFFSET
            ):
            # if the amount of appointments is big, make an offset
            meetings = meetings[len(meetings) // 2:]
    meetings.sort(key=lambda x: (
        x['office'] not in settings.AppointmentData.PRIORITY_OFFICES
    ))
    return meetings


@bot.notify_errors
@logger.catch_error
def check_appointment(driver: Driver, event: threading.Event):
    page = HomePage(driver)
    with cleared(event):
        driver.switch_to_tab(0)
        page.click_calendar()
    page = AppointmentPage(driver)
    account = driver.account
    while True:
        sleep(random.choice(settings.RequestTimeout.APPOINTMENT))
        with cleared(event):
            driver.switch_to_tab(0)
            with threading.Lock():
                driver.set_proxy(next(proxies))
            logger.log(f'{account.email}: checking appointments')
            breakpoint()
            page.refresh()
            page.language = 'en'
            page.matter_option = 'ARI'
            available_meetings = list(page.all_meetings)
            if not available_meetings:
                logger.log(f'{account.email}: no appointments have appeared')
                continue
            logger.log(
                f'{account.email}: new appointments have appeared' + (
                    '\n\t- ' + '\n\t- '.join(map(str, available_meetings))
                ), to_stdout=True
            )
            available_meetings = filter_available_meetings(
                available_meetings, account
            )
            logger.log(
                f'{account.email}: appointments after filter and sort' + (
                    '\n\t- ' + '\n\t- '.join(map(str, available_meetings))
                )
            )
            driver.save_snapshot(settings.SNAPSHOTS_PATH)
            driver.save_screenshot(settings.SCREENSHOTS_PATH)
            if account.updates.status == (
                    settings.DISABLE_APPOINTMENT_CHECKS_STATUS
                ):
                logger.log(
                    '{}: inappropriate status for making appointments'.format(
                        account.email
                    ), to_stdout=True
                )
                return True
            if not account.is_signed:
                for meeting in available_meetings:
                    try:
                        page.refresh()
                        is_success = page.schedule(meeting)
                        # TODO: check if meeting was scheduled successfully
                    except selenium_exceptions.NoSuchElementException:
                        continue
                    except Exception as e:
                        logger.log(
                            f'{account.email}: appointment {e.__class__}'
                        )
                    logger.log((
                        '{}: main was scheduled on {} at "{}" office'
                    ).format(
                        account.email, 
                        meeting['datetime'].strftime('%Y-%m-%d %H:%M'),
                        meeting['office']
                    ), to_stdout=True)
                    account.updates.update({
                        'office_signed': meeting['office'], 
                        'datetime_signed': meeting['datetime']
                    })
                    available_meetings = available_meetings[
                        available_meetings.index(meeting) + 1:
                    ]
                    break
                else:
                    logger.log(
                        f'{account.email}: unable to make an appointment'
                    )
                    continue
            scheduled_meetings = [
                {'datetime': x.datetime_signed, 'office': x.office_signed}
                for x in (account.updates, *account.dependents) 
                if x.datetime_signed is not None 
            ]
            logger.log(
                f'{account.email}: scheduled meetings' + (
                    '\n\t- ' + '\n\t- '.join(map(str, scheduled_meetings))
                )
            )
            for smeeting in scheduled_meetings:
                smeeting_start = smeeting['datetime'] - timedelta(
                    hours=settings.AppointmentData.HOUR_OFFICE_OFFSET)
                smeeting_end = smeeting['datetime'] + timedelta(
                    hours=settings.AppointmentData.HOUR_OFFICE_OFFSET)
                available_meetings = list(filter(lambda x: (
                    (
                        x['datetime'] <= smeeting_start or
                        x['datetime'] >= smeeting_end
                    ) 
                    if x['office'] != smeeting['office'] else True
                ), available_meetings))
            logger.log(
                f'{account.email}: meetings after time offset filter' + (
                    '\n\t- ' + '\n\t- '.join(map(str, available_meetings))
                )
            )
            for tab_index, dependent in enumerate(
                    sorted(account.dependents, key=lambda x: x.id), start=1
                ):
                if dependent.is_signed:
                    continue
                driver.switch_to_tab(tab_index)
                p = AppointmentPage(driver)
                p.language = 'en'
                driver.save_snapshot(settings.SNAPSHOTS_PATH)
                dependent.add_observer(bot)
                for meeting in available_meetings:
                    try:
                        p.refresh()
                        is_success = p.schedule(meeting)
                        # TODO: check if meeting was scheduled successfully
                    except selenium_exceptions.NoSuchElementException:
                        continue
                    except Exception as e:
                        logger.log(
                            f'{account.email}: {dependent.name} '
                            f'appointment {e.__class__}'
                        )
                    logger.log((
                        '{}: {} was scheduled on {} at "{}" office'
                    ).format(
                        account.email, dependent.name,
                        meeting['datetime'].strftime('%Y-%m-%d %H:%M'),
                        meeting['office']
                    ), to_stdout=True)
                    dependent.update({
                        'office_signed': meeting['office'], 
                        'datetime_signed': meeting['datetime']
                    })
                    available_meetings = available_meetings[
                        available_meetings.index(meeting) + 1:
                    ]
                    break
            sleep(3)


def main():
    threads = [
        threading.Thread(
            target=thread_checker, args=(account.to_dict(), applicants), 
            daemon=True
        ) for account, applicants in settings.ACCOUNTS.items()
    ]
    for thread in threads:
        thread.start()
    print("Parser started")
    bot.infinity_polling()
    print("Shutting down the parser")
    # Kill all instances of driver
    subprocess.call(
        settings.ChromeData.TASK_KILL_COMMAND.split(), 
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )


if __name__ == '__main__':
    main()
