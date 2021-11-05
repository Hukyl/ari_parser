import sys
from os import path
import random
import subprocess
from time import sleep
import threading
from datetime import datetime, timedelta
from itertools import chain
from typing import Callable, Iterable

from selenium.common import exceptions as selenium_exceptions
from datetimerange import DateTimeRange
from loguru import logger

from models.driver import Driver
from models.page import HomePage, AppointmentPage, ApplicantsPage
from models.account import Account, Dependent
from models import exceptions
from bot import Bot
import settings
from utils import cycle, cleared, waited, FrozenDict, safe_iter, Default


logger.remove(0)
logger.add(
    sys.stderr, format=(
        '[{time:YYYY-MM-DD HH:mm:ss}] [{level}] {extra[email]}: {message}'
    ), level="DEBUG"
)
logger.add(
    path.join(settings.LOGS_PATH, '{time:YYYY-MM-DD_HH-mm-ss}.log'), 
    format=(
        '[{time:YYYY-MM-DD HH:mm:ss}] [{level}] {extra[email]}: {message}'
    ), level="DEBUG", rotation="00:00"
)
proxies = cycle([''] if not settings.PROXIES else random.sample(
    settings.PROXIES, len(settings.PROXIES)
))
bot = Bot()


class Crawler:
    def __init__(self, account_data: FrozenDict, data: dict):
        self.account = self._create_account(account_data, data)
        self.driver = Driver(self.account)
        self.account.updates.add_observer(bot)
        for dependent in self.account.dependents:
            dependent.updates.add_observer(bot)
        self.logger = logger.bind(email=self.account.email)
        self.appropriate_status = threading.Event()
        self.access = threading.Event()
        self.access.set()
        self.init_driver()

    def init_driver(self):
        page = HomePage(self.driver)
        page.raw_get()
        page.language = 'en'
        if self.account.auth_token:
            self.driver.add_cookie({
                'name': settings.AUTH_TOKEN_COOKIE_NAME, 
                'value': self.account.auth_token,
            })
            self.logger.info("an auth token cookie is used")
        if self.account.session_id:
            self.driver.add_cookie({
                'name': settings.SESSION_ID_COOKIE_NAME, 
                'value': self.account.session_id,
            })
            self.logger.info("a session id cookie is used")        
        try:
            page.get()
        except exceptions.AuthorizationException as e:
            self.logger.error(str(e))
            bot.send_error(self.account.email, e)
            return
        self.driver.open_new_tab()  # reserve a tab for status checking
        self.driver.switch_to_tab(0)
        for dependent in self.account.dependents:
            self.driver.open_new_tab()
            p = HomePage(self.driver)
            p.get()
            p.language = 'en'
            p.click_applicants()
            p = ApplicantsPage(self.driver)
            p.set_applicant(dependent.name)
            dependent.updates.update(
                status=p.applicant_status, additional={'to_notify': False}
            )
            self.logger.debug(
                f"{dependent.name!r} status is {p.applicant_status}"
            )
        else:
            self.driver.switch_to_tab(0)            

    def update_proxy(self):
        with threading.Lock():
            self.driver.set_proxy(next(proxies))   

    @staticmethod
    def _create_account(account_data: FrozenDict, data: dict):
        if not Account.exists(email=account_data['email']):
            Account.create(account_data['email'], account_data['password'])
        account = Account(account_data['email'])
        account.update(password=account_data['password'])
        account.update(day_offset=data['day_offset'])
        account.update(unavailability_datetime=data['unavailability_datetime'])
        for name in data['dependents']:
            if not Dependent.exists(name):
                account.add_dependent(name)
        return account

    def update_status(self):
        page = HomePage(self.driver)
        has_changed = False
        with cleared(self.access):
            self.driver.switch_to_tab(-1)
            self.update_proxy()
            self.logger.debug(f'Set proxy to {self.driver.proxy}')
            self.logger.info('checking status')
            self.driver.get(page.URL)
            status = page.status
            if status == settings.DISABLE_APPOINTMENT_CHECKS_STATUS:
                self.appropriate_status.clear()  # stop scheduling
                self.logger.debug(
                    'Disable appointment checks, inapporpriate status'
                )
            else:
                self.appropriate_status.set()
            if status != self.account.updates.status:
                has_changed = True
                self.logger.info("status is {}", status)
                self.account.updates.update(
                    status=status,
                    additional={
                        'image': page.status_screenshot, 
                        'email': self.account.email
                    }
                )
                self.driver.save_snapshot(settings.SNAPSHOTS_PATH)
            else:
                self.logger.info("status has not changed")
            return has_changed

    def schedule_appointments(self):
        page = HomePage(self.driver)
        with waited(self.appropriate_status), cleared(self.access):
            self.driver.switch_to_tab(0)
            page.click_calendar()
            iterator = self._check_new_appointments()
            if not iterator:
                return
            settings.RequestTimeout.APPOINTMENT.value = (
                settings.RequestTimeout.BURST_APPOINTMENT
            )
            self.driver.save_snapshot(settings.SNAPSHOTS_PATH)
            self.driver.save_screenshot(settings.SCREENSHOTS_PATH)                
            is_ok = self._schedule_main(iterator)
            if not is_ok:
                return
            return self._schedule_dependents(iterator)

    def get_valid_meeting(self, meetings_iterator: 'safe_iter'):
        while meeting := next(meetings_iterator):
            if self.is_valid_meeting(meeting):
                return meeting
        return False

    def _check_new_appointments(self) -> chain:
        page = AppointmentPage(self.driver)
        self.driver.switch_to_tab(0)
        self.update_proxy()
        self.logger.info('checking appointments')
        page.refresh()
        page.language = 'en'
        page.matter_option = 'ARI'
        offices = list(filter(
            lambda x: x not in settings.AppointmentData.BLOCKED_OFFICES, 
            page.branch_options
        ))  # filter out inappropriate offices
        offices.sort(key=lambda x: (
            x in settings.AppointmentData.PRIORITY_OFFICES
        ), reverse=True)
        meetings_iterator = safe_iter(
            page.all_meetings(offices=offices)
        )
        breakpoint()
        meeting = self.get_valid_meeting(meetings_iterator)
        if not meeting:
            self.logger.info('no appointments have appeared')
            return False
        else:
            # push meeting back to the iterator
            return chain([meeting], meetings_iterator)

    def is_valid_meeting(self, meeting: dict) -> bool:
        min_datetime = (datetime.now() + timedelta(
            days=self.account.day_offset
        )).date()
        if meeting['datetime'].date() < min_datetime:
            self.logger.debug(f'Meeting {meeting} is invalid by day offset')
            return False
        elif any(
                    meeting['datetime'] in drange 
                    for drange in self.account.unavailability_datetime
                ):
            self.logger.debug(
                f'Meeting {meeting} is in unavailability periods'
            )
            return False
        else:
            applicants = [d.updates for d in self.account.dependents] + [
                self.account.updates
            ]
            scheduled_meetings = [
                {'datetime': x.datetime_signed, 'office': x.office_signed}
                for x in applicants
                if x.datetime_signed is not None 
            ]
            is_valid = all(
                meeting['datetime'] not in DateTimeRange(
                    smeeting['datetime'] - timedelta(
                        hours=settings.AppointmentData.HOUR_OFFICE_OFFSET
                    ), smeeting['datetime'] + timedelta(
                        hours=settings.AppointmentData.HOUR_OFFICE_OFFSET
                    )
                ) if meeting['office'] != smeeting['office'] else True
                for smeeting in scheduled_meetings
            )
            if is_valid:
                self.logger.debug(f'Meeting {meeting} is valid')
            else:
                self.logger.debug(
                    f"Meeting {meeting} is too close to scheduled meetings"
                )
            return is_valid

    def _schedule_main(self, meetings_iterator: 'safe_iter'):
        page = AppointmentPage(self.driver)
        if not self.account.is_signed:
            while meeting := self.get_valid_meeting(meetings_iterator):
                page.refresh()
                try:
                    is_success = page.schedule(meeting)
                    # TODO: check if meeting was scheduled successfully
                except selenium_exceptions.NoSuchElementException:
                    self.logger.warning(f'Meeting {meeting} is unavailable')
                except Exception as e:
                    self.logger.error("appointment {}", e.__class__)
                else:
                    self.logger.success(
                        'main was scheduled on {:%Y-%m-%d %H:%M} at '
                        '{!r} office',
                        meeting['datetime'], meeting['office']
                    )
                    self.account.updates.update(
                        office_signed=meeting['office'],
                        datetime_signed=meeting['datetime'],
                        additional={'email': self.account.email}
                    )
                    return is_success
        self.logger.warning('unable to make an appointment')
        return False

    def _schedule_dependents(self, meetings_iterator: 'safe_iter'):
        p = ApplicantsPage(self.driver)
        for tab_index, dependent in enumerate(
                    sorted(self.account.dependents, key=lambda x: x.id), 
                    start=1
                ):
            if dependent.is_signed or dependent.updates.status == (
                        settings.DISABLE_APPOINTMENT_CHECKS_STATUS
                    ):
                continue
            self.driver.switch_to_tab(tab_index)
            p.get_applicant_appointment()
            page = AppointmentPage(self.driver)
            page.language = 'en'
            self.driver.save_snapshot(settings.SNAPSHOTS_PATH)
            while meeting := self.get_valid_meeting(meetings_iterator):
                try:
                    page.refresh()
                    is_success = page.schedule(meeting)
                    if not is_success:
                        raise selenium_exceptions.NoSuchElementException
                    # TODO: check if meeting was scheduled successfully
                except selenium_exceptions.NoSuchElementException:
                    self.logger.warning(f'Meeting {meeting} is unavailable')                        
                except Exception as e:
                    self.logger.error(
                        f'{dependent.name!r} appointment {e.__class__}'
                    )
                else:
                    self.logger.success(
                        '{!r} was scheduled on {:%Y-%m-%d %H:%M} '
                        'at {!r} office',
                        dependent.name,
                        meeting['datetime'],
                        meeting['office']
                    )
                    dependent.updates.update(
                        office_signed=meeting['office'], 
                        datetime_signed=meeting['datetime'],
                        additional={
                            'email': self.account.email, 
                            'dependent_name': dependent.name
                        }
                    )
                    break
            else:
                # if couldn't make an appointment for any dependent, skip
                return False
        return True

    def _create_thread(
                self, func: Callable[[], bool], sleep_time_range: Default
            ):
        def infinite_loop():
            try:
                while True:
                    func()
                    sleep(random.choice(sleep_time_range.value))
            except Exception as e:
                self.logger.error(f'{e.__class__.__name__} occurred')
                bot.send_error(self.account.email, e.args[0])

        threading.Thread(target=infinite_loop, daemon=True).start()

    def start(self, *, checks: Iterable[settings.Check]):        
        checks_methods = {
            settings.Check.APPOINTMENT: {
                'method': self.schedule_appointments, 
                'sleep_time_range': settings.RequestTimeout.APPOINTMENT
            },
            settings.Check.STATUS: {
                'method': self.update_status,
                'sleep_time_range': settings.RequestTimeout.STATUS
            }
        }
        self.update_status()
        for check in set(checks):
            data = checks_methods[check]
            self._create_thread(data['method'], data['sleep_time_range'])


def main():
    for account, data in settings.ACCOUNTS.items():
        Crawler(account, data).start(checks=data['checks'])
    print("Parser started")
    bot.infinity_polling()
    print("Shutting down the parser")
    # Kill all instances of driver
    subprocess.call(
        settings.ChromeData.TASK_KILL_COMMAND.split(), 
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
