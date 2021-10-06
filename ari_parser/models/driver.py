from datetime import datetime
from time import sleep
import os
import sys
from typing import Optional, Union

from seleniumwire import webdriver

import settings
from utils.url import Url
from .user import User
from .page import LoginPage
from .logger import DefaultLogger
from .exceptions import InvalidCredentialsException


class Driver(webdriver.Chrome):
    NO_PROXY_IP = 'localhost,127.0.0.1,dev_server:8080'

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
        self.user = user
        super().__init__(
            executable_path=settings.ChromeData.PATH, 
            options=chrome_options,
            service_log_path=service_log_path,
            seleniumwire_options=seleniumwire_options
        )

    @property
    def is_redirected_to_login(self):
        return self.url == LoginPage.URL

    def log_in(self):
        page = LoginPage(self)
        self.get(page.URL)
        page.email = self.user.email
        page.password = self.user.password
        page.submit()
        if page.is_invalid_credentials:
            raise InvalidCredentialsException("invalid credentials")
        if (is_successful := not self.is_redirected_to_login):
            self.user.auth_token = self.get_cookie(
                settings.AUTH_TOKEN_COOKIE_NAME
            )['value']
            self.user.session_id = self.get_cookie(
                settings.SESSION_ID_COOKIE_NAME
            )['value']
        return is_successful

    @property
    def url(self):
        return Url(self.current_url)

    def safe_get(self, url: Union[Url, str]):
        self.get(url)
        if self.url != url:
            logger = DefaultLogger()
            logger.log(f'{self.user.email}: relogging in')
            self.user.auth_token = None
            self.delete_cookie(settings.AUTH_TOKEN_COOKIE_NAME)
            is_successful = self.log_in()
            if not is_successful:
                logger.log(f'{self.user.email}: unable to log in')
            self.get(url)
        return True

    def get(self, url: Union[Url, str]):
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
                f"{now}__{self.user.email}__{self.url.rsplit()[1]}.html"
            ), 'w', encoding='utf-8') as file:
            file.write(self.page_source)

    def open_new_tab(self):
        self.execute_script("window.open('', '_blank').focus()")
        return True

    def switch_to_tab(self, index:int, /):
        self.switch_to_window(self.window_handles[index])
        return True

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass
