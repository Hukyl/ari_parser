from abc import ABC, abstractmethod
from time import sleep
from datetime import datetime
from random import choice

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.common import exceptions

from utils.url import Url
from settings import locators


class BasePage(ABC):
    """
    Base class to initialize the base page that will be called from all
    pages
    """
    URL = Url("https://ari.sef.pt/")
    LOCATORS = locators.BasePageLocators

    def __init__(self, driver):
        self.driver = driver

    def __getattr__(self, attr):
        locator = getattr(self.LOCATORS, attr.upper())
        sleep(1)
        webelement = self.get_webelement(locator)
        webelement.found_by = locator
        return webelement

    def get_webelement(self, locator: tuple[str, str], *, start_element=None):
        return WebDriverWait(start_element or self.driver, 3).until(
            EC.presence_of_element_located(locator)
        )

    def change_language(self, lang_code: str):
        Select(self.language_select).select_by_value(lang_code)
        return True

    def enter_input(self, webelement, value:str) -> True:
        for symbol in value.strip():
            sleep(0.1)
            webelement.send_keys(symbol)
        return True

    @staticmethod
    def select_option(select_webelement, value:str) -> True:
        Select(select_webelement).select_by_visible_text(value)
        return True

    @staticmethod
    def get_selected_option(select_webelement):
        return Select(select_webelement).first_selected_option.text

    @staticmethod
    def get_select_options(select_webelement):
        return [x.text for x in Select(select_webelement).options]


class HomePage(BasePage):
    URL = BasePage.URL / 'ARIApplication.aspx'
    LOCATORS = locators.HomePageLocators

    def click_calendar(self):
        self.calendar_button.click()
        return True

    def click_applicants(self):
        self.applicants_button.click()
        return True

    @property
    def status(self):
        return self.status_span.text.strip()

    @property
    def status_screenshot(self):
        return self.status_outer_table.screenshot_as_png


class LoginPage(BasePage):
    URL = BasePage.URL / 'Account' / 'Entrada.aspx'
    LOCATORS = locators.LoginPageLocators

    @property
    def email(self):
        return self.email_input.get_property('value')

    @email.setter
    def email(self, value: str):
        self.enter_input(self.email_input, value)

    @property
    def password(self):
        return self.password_input.get_property('value')

    @password.setter
    def password(self, value: str):
        self.enter_input(self.password_input, value)

    @property
    def error(self):
        try:
            return self.error_span.text.strip()
        except exceptions.TimeoutException:
            return None

    @property
    def is_invalid_credentials(self):
        return self.error in [
            'Invalid user or password', 
            'Utilizador ou palavra chave inválida'
        ]

    def submit(self):
        self.submit_button.click()
        return True


class ApplicantsPage(BasePage):
    URL = BasePage.URL / 'ARIRF.aspx'
    LOCATORS = locators.ApplicantsPageLocators

    def set_applicant(self, name: str):
        try:
            return self.table.find_element('xpath', f'//td[.={name}]/../td[0]')
        except exceptions.TimeoutException:
            raise ValueError(
                f'unable to locate element with name "{name}"'
            ) from None

    def get_applicant_appointment(self):
        self.applicant_appointment_button.click()
        return True


class AppointmentPage(ABC, BasePage):
    URL = BasePage.URL / 'ARIAgenda.aspx'
    LOCATORS = locators.AppointmentPageLocators

    @abstractmethod
    def get_schedule_times(self):
        pass

    def schedule(self, options: list, *args, **kwargs) -> dict:
        office = choice(options)
        self.branch_option = office
        date = min([
            datetime.strptime('%Y - %B', x) for x in self.dates
        ])
        self.date = date.strftime('%Y - %B')
        day = min([
            f"0{x.lstrip('0')}" for x in self.days
        ]).lstrip()
        date = date.replace(day=int(day))
        self.day = day
        self.time = (time := min(
            self.get_schedule_times(date, *args, **kwargs)
        ))
        hour, minute = map(
            lambda x: int(x.lstrip('0')), time.split(':')
        )
        date = date.replace(hour=hour, minute=minute)
        self.submit()
        return {'office': office, 'date': date}

    @property
    def matter_option(self):
        try:
            return Select(self.matter_select).first_selected_option
        except exceptions.NoSuchElementException:
            return None

    @property
    def matter_options(self):
        return [x.text for x in Select(self.matter_select).options]

    @matter_option.setter
    def matter_option(self, value: str):
        Select(self.matter_select).select_by_visible_text(value)

    @property
    def branch_options(self):
        return [x.text for x in Select(self.branch_select).options]

    @property
    def branch_option(self):
        try:
            return Select(self.branch_select).first_selected_option
        except exceptions.NoSuchElementException:
            return None

    @branch_option.setter
    def branch_option(self, value: str):
        Select(self.branch_select).select_by_visible_text(value)

    @property
    def times(self):
        return [x.text for x in Select(self.time_select).options]

    @property
    def time(self):
        try:
            return Select(self.time_select).first_selected_option
        except exceptions.NoSuchElementException:
            return None

    @time.setter
    def time(self, value: str):
        Select(self.time_select).select_by_visible_text(value)

    @property
    def dates(self):
        return [x.text for x in Select(self.date_select).options]

    @property
    def date(self):
        try:
            return Select(self.date_select).first_selected_option
        except exceptions.NoSuchElementException:
            return None
    
    @date.setter
    def date(self, value: str):
        Select(self.date_select).select_by_visible_text(value)

    @property
    def days(self):
        return [x.text for x in Select(self.day_select).options]

    @property
    def day(self):
        try:
            return Select(self.day_select).first_selected_option
        except exceptions.NoSuchElementException:
            return None
    
    @day.setter
    def day(self, value: str):
        Select(self.day_select).select_by_visible_text(value)

    def submit(self):
        self.submit_button.click()

    def refresh(self):
        self.refresh_button.click()


class MainAppointmentPage(AppointmentPage):
    def get_schedule_times(self, *args, **kwargs):
        return self.times


class DependentAppointmentPage(AppointmentPage):
    def schedule(
            self, options: list, owner_datetime: datetime, 
            owner_office: str, min_hour_offset: int = 0
        ) -> dict:
        if owner_office not in options:
            return super().schedule(options, owner_datetime, min_hour_offset)
        else:
            data = super().schedule([owner_office])
        return data

    def get_schedule_times(
                self, approximate_date: datetime, start_date: datetime, 
                min_hour_offset: int = 0
            ):
        if start_date.date() == approximate_date:
            start_time = start_date.time()
            start_time = start_time.replace(
                hour=start_time.hour + min_hour_offset
            )
            return filter(lambda x: x > start_time, self.times)
        else:
            return self.times
