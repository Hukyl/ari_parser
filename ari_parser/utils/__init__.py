from functools import wraps
import re
from typing import Iterable, TypeVar, Union, Callable
import threading
import collections
from contextlib import contextmanager

T = TypeVar('T')
S = TypeVar('S')


def safe_iter(iterable: Iterable[T], default_value: S = None) -> Union[T, S]:
    """
    Iterator over the itetable and yield error_value infinitely
    
    Args:
        iterable (Iterable[T])
        default_value (S, optional): will be yielded after end of iterable
    
    Yields:
        Union[T, S]: T if it is from iterable else S
    """
    try:
        while True:
            yield next(iterable)
    except StopIteration:
        while True:
            yield default_value


class Default:
    """
    Usage:
        ```
        >>> d = Default(3, stash_count=2)
        >>> d.value
        3
        >>> d.value = 5
        >>> d.value
        5
        >>> d.value
        5
        >>> d.value
        3
        ```
    
    Attributes:
        default_stash_count (int): total 
        default_value (T): default value
        stash_count (int): current appeal times set variable will be available
        value (T): current value
    """

    def __init__(self, default_value: T, *, stash_count: int = 5):
        self.default_value = default_value
        self.default_stash_count = stash_count
        self.__stash_count = None
        self.__value = None

    @property
    def value(self) -> T:
        if self.__value:
            self.stash_count -= 1
            if self.stash_count <= 0:
                self.__value = None
                self.stash_count = None
        return self.__value or self.default_value

    @value.setter
    def value(self, value: T):
        self.__value = value
        self.stash_count = self.default_stash_count    


def xor(parameters: list[str]):
    """
    Accept only one of given parameters.
    Used as a decorator.
    Works only with keyword-only parameters.
    
    Args:
        parameters (list[str]): parameters to be checked
    
    Returns:
        T: Same type as decorated function
    """

    def outer(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def inner(*args, **kwargs) -> T:
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
def cleared(event: threading.Event) -> None:
    """
    Wait until event is set, and block it until end of code block.
    Used as as context manager
    
    Args:
        event (threading.Event): event to be cleared
    
    Yields:
        None: Description
    """
    event.wait()
    event.clear()
    try:
        yield
    finally:
        event.set()


@contextmanager
def waited(event: threading.Event) -> None:
    """
    Wait until the event is set to True and continue execution.
    Used as a context manager
    
    Args:
        event (threading.Event): event to be waited
    
    Yields:
        None: ...
    
    """
    event.wait()
    yield


class FrozenDict(collections.Mapping):
    """
    Immutable dict.
    Can be hashed and used in usual dict keys
    """

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


def cycle(iterable: Iterable[T], /) -> T:
    """
    Iterate infinitely across items in iterable
    
    Args:
        iterable (Iterable[T]): iterable to be iterated through
    
    Yields:
        T: item in iterable
    """
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
