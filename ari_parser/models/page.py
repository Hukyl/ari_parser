from time import sleep

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.common import exceptions

from utils.url import Url
from settings import locators


class BasePage(object):
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
