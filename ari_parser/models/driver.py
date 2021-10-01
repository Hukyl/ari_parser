from abc import ABC, abstractmethod
from functools import wraps
import os
import sys
from typing import Optional, Union

from selenium import webdriver

import settings
from utils.url import Url
from .user import User
from .page import LoginPage
from .logger import Logger


def preserve_start_url(func):
    @wraps(func)
    def inner(*args, **kwargs):
        self = args[0]
        start_url = self.url
        result = func(*args, **kwargs)
        self.get(start_url)
        return result
    return inner


class BaseDriver(ABC):
    @abstractmethod
    def get(self, url: Url):
        pass

    @abstractmethod
    @property
    def url(self):
        pass


class Driver(webdriver.Chrome, BaseDriver):
    def __init__(
            self, user: User,
            *, headless:Optional[bool]=settings.ChromeData.HEADLESS
            ):
        """
        Create a Chrome webdriver

        :keyword arguments:
            headless:bool=True - to set Chrome to be headless
        :return:
            driver:selenium.webdriver.Chrome
        """
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation"]
        )
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            "--disable-blink-features=AutomationControlled"
        )  # these options bypass CloudFare protection
        chrome_options.add_argument("--log-level=OFF")  # remove console output
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-logging"]
        )
        service_log_path = os.devnull if sys.platform == 'linux' else 'NUL'
        if headless:
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--headless")
            if sys.platform == 'linux':
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument('--disable-dev-shm-usage')
        self.user = user
        super().__init__(
            executable_path=settings.ChromeData.PATH, 
            options=chrome_options,
            service_log_path=service_log_path,
        )

    @property
    def is_redirected_to_login(self):
        return self.url == LoginPage.URL

    @preserve_start_url
    def log_in(self):
        page = LoginPage(self)
        self.get(page.URL)
        page.email = self.user.email
        page.password = self.user.password
        page.submit()
        return not self.is_redirected_to_login

    @property
    def url(self):
        return Url(self.current_url)

    def safe_get(self, url: Union[Url, str])):
        self.get(url)
        if self.is_redirected_to_login:
            Logger().log(f'{self.user.email}: relogging in')
            self.log_in()
        self.get(url)
        return

    def get(self, url: Union[Url, str]):
        if isinstance(url, Url):
            url = url.url
        return super().get(url)

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass
