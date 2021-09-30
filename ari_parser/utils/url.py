from dataclasses import dataclass
from typing import Union


@dataclass(eq=False)
class Url(object):
    url: str

    def __post_init__(self):
        self.url = self.url.rstrip('/')

    @property
    def path(self):
        if '?' not in self.url:
            return self.url
        return self.url[:self.url.rfind('?')]

    @property
    def params(self):
        if '?' not in self.url:
            return {}
        return self.decode_params(self.url[self.url.rfind('?'):])

    @params.setter
    def params(self, params:dict[str, Union[str, list[str]]]):
        if not params:
            self.url = self.path
        self.url = f'{self.path}{self.encode_params(params)}'

    @staticmethod
    def decode_params(params_str:str):
        result = {}
        for param in params_str.lstrip('?').split('&'):
            k, v = param.split('=', maxsplit=1)
            if k in result:
                if isinstance(result[k], list):
                    result[k].append(v)
                else:
                    result[k] = [result[k], v]
            else:
                result[k] = v
        return result

    @staticmethod
    def encode_params(params:dict[str, Union[str, list[str]]]):
        result_str = '?'
        for k, v in params.items():
            if isinstance(v, list):
                for item in v:
                    result_str += f"{k}={item}&"
            else:
                result_str += f"{k}={v}&"
        return result_str.rstrip('&')

    @property
    def parent(self):
        return self.__class__(self.url.rsplit('/', maxsplit=1)[0])

    def __truediv__(self, other:Union[str, dict]) -> 'Url':
        if isinstance(other, dict):
            return self.__class__(f"{self.url}/{self.encode_params(other)}")
        return self.__class__(f"{self.url}/{other}")

    def __copy__(self):
        return self.__class__(self.url)

    def rsplit(self):
        return self.parent, self.url.rsplit('/', maxsplit=1)[1]

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.path == other.path
        elif isinstance(other, str):
            other = self.__class__(other)
            return self == other
        else:
            return False

    def __add__(self, other: Union[str, dict]) -> 'Url':
        if isinstance(other, dict):
            return self.__class__(f"{self.url}{self.encode_params(other)}")
        return self.__class__(f"{self.url}{other}")

    def __str__(self):
        return self.url

    def format(self, *args, **kwargs):
        return self.__class__(self.url.format(*args, **kwargs))
