from functools import wraps
import re
from typing import Iterable
from threading import Event
import collections
from contextlib import contextmanager


def xor(parameters: list):
    """
    Accept only one of given parameters

    Works only with keyword-only parameters
    """

    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            entries = len([x for x in parameters if x in kwargs])
            if entries == 0:
                raise ValueError(
                    f'one of {", ".join(parameters)} must be passed'
                )
            elif entries > 1:
                raise ValueError(
                    f'only one of {", ".join(parameters)} must be passed'
                )
            else:
                return func(*args, **kwargs)
        return inner
    return outer



@contextmanager
def cleared(event: Event):
    event.wait()
    event.clear()
    try:
        yield
    finally:
        event.set()


class FrozenDict(collections.Mapping):
    """Don't forget the docstrings!!"""

    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def items(self):
        for k, v in self._d.items():
            yield (k, v)

    def to_dict(self):
        return self._d

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        # It would have been simpler and maybe more obvious to 
        # use hash(tuple(sorted(self._d.iteritems()))) from this discussion
        # so far, but this solution is O(n). I don't know what kind of 
        # n we are going to run into, but sometimes it's hard to resist the 
        # urge to optimize when it will gain improved algorithmic performance.
        if self._hash is None:
            hash_ = 0
            for pair in self.items():
                hash_ ^= hash(pair)
            self._hash = hash_
        return self._hash


def cycle(iterable: Iterable):
    while True:
        for x in iterable:
            yield x


def validate_email(s: str) -> bool:
    pattern = R"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}
~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09
\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9]
(?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?
[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:
[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-
\x7f])+)\])""".replace('\n', '')
    return hasattr(re.search(pattern, s), 'group')


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs
            )
        return cls._instances[cls]
