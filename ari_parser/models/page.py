from abc import ABC
from datetime import datetime
from time import sleep
from typing import Union

from selenium.common import exceptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from settings import locators, BASE_URL
from utils.url import Url


class BasePage(ABC):
    """
    Base class to initialize the base page that will be called from all
    pages
    """
    URL = Url(BASE_URL)
    LOCATORS = locators.BasePageLocators

    def __init__(self, driver):
        self.driver = driver

    def __getattr__(self, attr):
        locator = getattr(self.LOCATORS, attr.upper())
        webelement = self.get_webelement(locator)
        webelement.found_by = locator
        return webelement

    def get_webelement(self, locator: tuple[str, str], *, start_element=None):
        return WebDriverWait(start_element or self.driver, 3).until(
            EC.presence_of_element_located(locator)
        )

    @property
    def language(self):
        return Select(self.language_select).first_selected_option

    @language.setter
    def language(self, lang_code: str):
        Select(self.language_select).select_by_value(lang_code)

    @staticmethod
    def enter_input(webelement, value: str) -> True:
        for symbol in value.strip():
            sleep(0.1)
            webelement.send_keys(symbol)
        return True

    def get(self):
        sleep(1)
        self.driver.get(self.URL)

    def raw_get(self):
        self.driver.raw_get(self.URL)

    @property
    def reached(self) -> bool:
        return self.driver.url == self.URL

    @staticmethod
    def select_option(select_webelement, value: str) -> True:
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
            self.table.find_element(
                'xpath', f'//td[.="{name}"]/../td[1]/input'
            ).click()
        except exceptions.TimeoutException:
            raise ValueError(
                f'unable to locate element with name "{name}"'
            ) from None

    def get_applicant_appointment(self):
        self.applicant_calendar_button.click()
        return True

    @property
    def applicant_status(self):
        return self.applicant_status_span.text


class AppointmentPage(BasePage):
    URL = BasePage.URL / 'ARIAgenda.aspx'
    LOCATORS = locators.AppointmentPageLocators

    def schedule(self, data: dict[str, Union[datetime, str]]) -> bool:
        self.matter_option = 'ARI'
        self.branch_option = data['office']
        self.date = data['datetime'].strftime('%Y - %B')
        self.day = str(data['datetime'].day)
        self.time = data['datetime'].strftime('%H:%M')
        self.submit()
        try:
            _ = self.matter_option and self.branch_option and self.date
        except exceptions.TimeoutException:
            # if no such element are present on the page,
            # then we got to another page and scheduling succeeded
            return True
        else:
            return False

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

    def all_meetings(self, *, offices: list[str] = None):
        for office in offices or self.branch_options:
            self.branch_option = office
            for date in self.dates:
                self.date = date
                date = datetime.strptime(date, '%Y - %B')
                for day in self.days:
                    self.day = day
                    for time in self.times:
                        yield {'datetime': datetime.combine(
                            date.replace(day=int(day)).date(), 
                            datetime.strptime(time, '%H:%M').time()
                        ), 'office': office}

    def submit(self):
        self.submit_button.click()

    def refresh(self):
        self.refresh_button.click()
