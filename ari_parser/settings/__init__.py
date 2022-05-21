from os import environ
import sys
from enum import Enum, auto

from datetimerange import DateTimeRange

from utils import FrozenDict, Default


class Check(Enum):
    STATUS = auto()
    APPOINTMENT = auto()


# TODO: Set up `unavailability_datetime` for `dependents`
ACCOUNTS: dict[FrozenDict, dict] = {}

BASE_URL = environ.get('BASE_URL')

BOT_TOKEN = environ.get('BOT_TOKEN')

AUTH_TOKEN_COOKIE_NAME = '.ASPXAUTH'
SESSION_ID_COOKIE_NAME = 'ASP.NET_SessionId'

DB_NAME = 'db.sqlite3'
SNAPSHOTS_PATH = 'snapshots'
SCREENSHOTS_PATH = 'screenshots'
LOGS_PATH = 'logs'

LOG_LEVEL = "DEBUG"  # ("DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR")


class RequestTimeout:
    ERROR = Default(range(10 * 60, 15 * 60 + 1))  # in seconds
    STATUS = Default(range(58 * 60, 62 * 60 + 1))  # in seconds
    APPOINTMENT = Default(range(1 * 60, 3 * 60 + 1), stash_count=60)
    BURST_APPOINTMENT = range(10, 15)  # in seconds


PROXIES = []
PAGE_LOAD_TIMEOUT = 10  # max number of seconds to load the page

DISABLE_APPOINTMENT_CHECKS_STATUS = 'Under review'


class AppointmentData:
    PRIORITY_OFFICES = []
    BLOCKED_OFFICES = []
    HOUR_OFFICE_OFFSET = 3


class ChromeData:
    PATH = environ.get('CHROMEDRIVER_PATH')
    TASK_KILL_COMMAND = (
        'taskkill /F /IM chrome.exe' if sys.platform.startswith('win') 
        else 'killall chrome'
    )
    HEADLESS: bool = False
