import os
import sys
from datetime import datetime
from typing import Optional, Union

from loguru import logger
from seleniumwire import webdriver

from .account import Account
from .exceptions import InvalidCredentialsException, AuthorizationException
from .page import LoginPage
import settings
from utils.url import Url


class Driver(webdriver.Chrome):
    NO_PROXY_IP = 'localhost,127.0.0.1,dev_server:8080'

    def __init__(
            self, account: Account,
            *, headless: Optional[bool] = settings.ChromeData.HEADLESS
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
        chrome_options.add_argument("--remote-debugging-port=9222")
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
    def is_redirected_to_login(self) -> bool:
        """
        Check if current driver url is equal to login page's url.
        
        Returns:
            bool
        """
        return self.url == LoginPage.URL

    def log_in(self) -> True:
        """
        Log in with `self.account`
        
        Returns:
            True
        
        Raises:
            AuthorizationException: unable to log in
            InvalidCredentialsException
        """
        # TODO: Relocate setting the cookies to outer scope
        # TODO: Remove account from driver 
        page = LoginPage(self)
        self.raw_get(page.URL)
        page.email = self.account.email
        page.password = self.account.password
        page.submit()
        if page.is_invalid_credentials:
            raise InvalidCredentialsException("invalid credentials")
        elif self.is_redirected_to_login:
            raise AuthorizationException('unable to log in')
        self.account.update(auth_token=self.get_cookie(
            settings.AUTH_TOKEN_COOKIE_NAME
        )['value'])
        self.account.update(session_id=self.get_cookie(
            settings.SESSION_ID_COOKIE_NAME
        )['value'])
        return True

    @property
    def url(self) -> Url:
        return Url(self.current_url)

    def get(self, url: Union[Url, str]) -> bool:
        """
        Get url safely. 
        If redirected to login page, re-login and get the needed url again.
        
        Args:
            url (Union[Url, str]): url to get
        
        Returns:
            True
        """
        is_successful = True
        self.raw_get(url)
        if self.url != url:
            self.logger.info('relogging in')
            self.account.update(auth_token=None)
            self.delete_cookie(settings.AUTH_TOKEN_COOKIE_NAME)
            is_successful = self.log_in()
            if not is_successful:
                self.logger.error('unable to log in')
            self.raw_get(url)
        return is_successful

    def raw_get(self, url: Union[Url, str]) -> None:
        """
        Just get the needed url
        
        Args:
            url (Union[Url, str])
        
        Returns:
            None
        """
        if isinstance(url, Url):
            url = url.url
        return super().get(url)

    def set_proxy(self, proxy: Union[str, None]) -> True:
        """
        Set proxy for the driver.
        If no proxy is passed, proxy is removed.
        Proxy with authentication are supported.
        Supported proxy types are HTTP(S), SOCKS4 and SOCKS5
        
        Args:
            proxy (Union[str, None]): proxy to be set
        
        Returns:
            True
        
        Raises:
            ValueError: invalid proxy type
        """
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

    def save_snapshot(self, dirname: Optional[str] = '') -> None:
        """
        Save page source as html-file to specified directory.
        
        Args:
            dirname (Optional[str], optional): Directory to save to
        """
        if not dirname:
            dirname = ''
        os.makedirs(dirname, exist_ok=True)
        now = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        with open(
                os.path.join(
                    dirname, 
                    f"{now}__{self.account.email}__{self.url.rsplit()[1]}.html"
                ), 'w', encoding='utf-8') as file:
            file.write(self.page_source)

    def save_screenshot(self, dirname: Optional[str] = '') -> None:
        """
        Save screenshot of current tab to specified directory.

        Args:
            dirname (Optional[str], optional): Directory to save to
        """
        if not dirname:
            dirname = ''        
        os.makedirs(dirname, exist_ok=True)
        now = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        filename = os.path.join(
            os.path.abspath(os.curdir), dirname, 
            f"{now}__{self.account.email}__{self.url.rsplit()[1]}.png"
        )
        super().save_screenshot(filename)

    def open_new_tab(self) -> True:
        """
        Open to tab and switch to it.
        
        Returns:
            True
        """
        self.execute_script("window.open('', '_blank')")
        tab_name = (set(self.window_handles) - set(self.tabs)).pop()
        index = self.tabs.index(self.current_window_handle) + 1
        self.tabs.insert(index, tab_name)
        self.switch_to_tab(index)
        return True

    def close_tab(self) -> True:
        """
        Close current tab and switch to the very first tab.
        
        Returns:
            True
        """
        tab_name = self.current_window_handle
        self.execute_script('window.close();')
        self.tabs.remove(tab_name)
        self.switch_to_tab(0)
        return True

    def switch_to_tab(self, index: int) -> True:
        """
        Switch ot tab by indexing the list of tabs
        
        Args:
            index (int): tab index in list, 0-based
        
        Returns:
            True
        """
        tab_name = self.tabs[index]
        self.switch_to.window(tab_name)
        return True

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass
