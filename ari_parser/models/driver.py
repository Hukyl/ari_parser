from abc import ABC, abstractmethod
import os
import sys
from typing import Optional, Union

from selenium import webdriver

import settings
from utils.url import Url


class BaseDriver(ABC):
    @abstractmethod
    def get(self, url: Url):
        pass

    @abstractmethod
    @property
    def url(self):
        pass




class WebDriver(webdriver.Chrome, BaseDriver):
    def __init__(
            self, *args, 
            headless:Optional[bool]=settings.ChromeData.HEADLESS, **kwargs
            ):
        """
        Create a Chrome webdriver

        :keyword arguments:
            headless:bool=True - to set Chrome to be headless
        :return:
            driver:selenium.webdriver.Chrome
        """
        kwargs.pop('options', None)
        kwargs.pop('executable_path', None)
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
        super().__init__(
            *args,
            executable_path=settings.ChromeData.PATH, 
            options=chrome_options,
            service_log_path=service_log_path,
            **kwargs
        )

    @property
    def url(self):
        return Url(self.current_url)

    def get(self, url:Union[Url, str]):
        if isinstance(url, Url):
            url = url.url
        return super().get(url)

    def __del__(self):
        try:
            self.quit()
        except Exception:
            pass
