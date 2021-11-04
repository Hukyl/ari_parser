from datetime import datetime
from time import sleep
import os
import sys
from typing import Optional, Union

from seleniumwire import webdriver
from loguru import logger

import settings
from utils.url import Url
from .account import Account
from .page import LoginPage
from .exceptions import InvalidCredentialsException


class Driver(webdriver.Chrome):
    NO_PROXY_IP = 'localhost,127.0.0.1,dev_server:8080'

    def __init__(
            self, account: Account,
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
        seleniumwire_options = {'proxy': {'no_proxy': self.NO_PROXY_IP}}
        if headless:
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--headless")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-logging"]
            )
            if sys.platform == 'linux':
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument('--disable-dev-shm-usage')
        self.account = account
        self.logger = logger.bind(email=self.account.email)
        super().__init__(
            executable_path=settings.ChromeData.PATH, 
            options=chrome_options,
            service_log_path=service_log_path,
            seleniumwire_options=seleniumwire_options
        )
        self.tabs = self.window_handles[:]

    @property
    def is_redirected_to_login(self):
        return self.url == LoginPage.URL

    def log_in(self):
        page = LoginPage(self)
        self.get(page.URL)
        page.email = self.account.email
        page.password = self.account.password
        page.submit()
        if page.is_invalid_credentials:
            raise InvalidCredentialsException("invalid credentials")
        elif (is_successful := not self.is_redirected_to_login):
            self.account.update(auth_token=self.get_cookie(
                settings.AUTH_TOKEN_COOKIE_NAME
            )['value'])
            self.account.update(session_id=self.get_cookie(
                settings.SESSION_ID_COOKIE_NAME
            )['value'])
        return is_successful

    @property
    def url(self):
        return Url(self.current_url)

    def get(self, url: Union[Url, str]):
        self.raw_get(url)
        if self.url != url:
            self.logger.info('relogging in')
            self.account.auth_token = None
            self.delete_cookie(settings.AUTH_TOKEN_COOKIE_NAME)
            is_successful = self.log_in()
            if not is_successful:
                self.logger.error('unable to log in')
            self.raw_get(url)
        return True

    def raw_get(self, url: Union[Url, str]):
        sleep(1)
        if isinstance(url, Url):
            url = url.url
        return super().get(url)

    def set_proxy(self, proxy:str):
        proxies = {'no_proxy': self.NO_PROXY_IP}
        if not proxy:
            pass
        elif proxy.startswith('http'):
            proxies['https'] = proxy
        elif proxy.startswith('socks'):
            proxies['http'] = proxies['https'] = proxy
        else:
            raise ValueError('unsupported proxy type')
        self.proxy = proxies
        return True

    def save_snapshot(self, dirname: str):
        os.makedirs(dirname, exist_ok=True)
        now = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        with open(
            os.path.join(
                dirname, 
                f"{now}__{self.account.email}__{self.url.rsplit()[1]}.html"
            ), 'w', encoding='utf-8') as file:
            file.write(self.page_source)

    def save_screenshot(self, dirname: str):
        os.makedirs(dirname, exist_ok=True)
        now = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        filename = os.path.join(
            os.path.abspath(os.curdir), dirname, 
            f"{now}__{self.account.email}__{self.url.rsplit()[1]}.png"
        )
        super().save_screenshot(filename)

    def open_new_tab(self):
        self.execute_script("window.open('', '_blank')")
        tab_name = (set(self.window_handles) - set(self.tabs)).pop()
        index = self.tabs.index(self.current_window_handle) + 1
        self.tabs.insert(index, tab_name)
        self.switch_to_tab(index)
        return True

    def close_tab(self):
        tab_name = self.current_window_handle
        self.execute_script('window.close();')
        self.tabs.remove(tab_name)
        self.switch_to_tab(0)
        return True

    def switch_to_tab(self, index:int, /):
        tab_name = self.tabs[index]
        self.switch_to_window(tab_name)
        return True

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass
