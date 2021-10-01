import os
from datetime import datetime as dt

from utils import Singleton



class Logger(metaclass=Singleton):
    MAX_SIZE = 1000 * 1024  # 1 MB

    def __init__(self):
        self.log_count = 0
        self.base_path = os.path.join(
            'logs', dt.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        )
        os.makedirs(self.base_path, exist_ok=False)
        self.logfile = self.create_logfile()

    def create_logfile(self):
        """
        Create a log file, increase `log_count` and return it

        :return:
            file(_io.TextIOWrapper): open(
                base_path + 'log' + count, mode='w', encoding='utf-8'
            )
        """
        self.log_count += 1
        return open(
            os.path.join(self.base_path, f"log{self.log_count}.log"), 
            'w', encoding="utf-8"
        )

    def update_logfile(self):
        """
        Update log file, close previous one

        :return:
            success_status(bool)=True
        """
        self.logfile.close()
        self.logfile = self.create_logfile()
        return True

    @property
    def logfile_size_ok(self) -> bool:
        return os.path.getsize(self.logfile.name) < self.MAX_SIZE

    def log(self, message:str, /, *, kind:str) -> None:
        """
        Log message to console and to file

        :positional arguments:
            message(str): what message will be logged
        :keyword arguments:
            kind(str): what type of log will be used
        :raise:
            AssertionError: if `kind` not in Logger.LOG_LEVELS
        :return: None
        """
        assert (
            info := self.LOG_LEVELS.get(kind.lower())
        ) is not None, "unsupported message kind"
        if self.LOG_LEVELS[self.log_level] <= info:
            message = (
                f"[{dt.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"[{kind.upper()}] {message}"
            )
            self.logfile.write(message + "\n")
            self.logfile.flush()
            # print(message)
            if not self.logfile_size_ok:
                self.update_logfile()

    def catch_error(self, f):
        """
        Log errors if function raises any
        type: instancemethod, decorator
        """
        def inner(*args, **kwargs):
            try:
                res = f(*args, **kwargs)
            except Exception as e:
                self.log(
                    f"Function {f.__name__} raised {e.__class__.__name__}:{e}"
                )
            else:
                return res
        return inner

    def __del__(self):
        self.logfile.close()
