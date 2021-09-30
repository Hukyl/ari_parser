from time import sleep

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select

from utils.url import Url
from settings import locators
from .driver import BaseDriver


class BasePage(object):
    """
    Base class to initialize the base page that will be called from all
    pages
    """
    URL = Url("https://ari.sef.pt/")
    LOCATORS = object

    def __init__(self, driver: BaseDriver):
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

    def enter_input(self, webelement, value:str) -> True:
        webelement.click()
        webelement.send_keys(Keys.HOME)
        webelement.send_keys(Keys.SHIFT, Keys.END)
        webelement.send_keys(Keys.BACKSPACE)
        webelement = (
            self.get_webelement(webelement.found_by) 
            if hasattr(webelement, 'found_by') else webelement
        )
        for symbol in value:
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

    @property
    def status(self):
        return self.status_span.text


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

    def submit(self):
        self.submit_button.click()
        return True