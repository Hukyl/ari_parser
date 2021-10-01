from abc import ABC
from typing import Callable, AnyStr, Any

from .db import UserDatabase


class Observable(ABC):
    def __init__(self):
        self.observers = []
        self.composite = {'value': self, 'image': None}

    def add_observer(self, obs: Callable):
        self.observers.append(obs)

    def remove_observer(self, obs: Callable):
        self.observers.remove(obs)

    def notify_observers(self, *args, **kwargs):
        for observer in self.observers:
            observer(self, *args, **kwargs)


class User:
    _db = UserDatabase()

    def __init__(self, email: str):
        data = self._db.get_user(email=email)
        for k, v in data.items():
            self.__dict__[k] = v
        self.updates = Updates(data['id'])

    @classmethod
    def create_user(cls, *args, **kwargs):
        cls._db.add_user(*args, **kwargs)

    @classmethod
    def exists(cls, email: str):
        return cls._db.check_email_exists(email)

    def __setattr__(self, attr: str, value: Any):
        self._db.change_user(self.id, **{attr: value})
        super().__setattr__(attr, value)


class Updates(Observable):
    _db = UserDatabase()

    def __init__(self, owner: User):
        super().__init__()
        self.owner = owner
        for k, v in self._db.get_updates(owner.id).items():
            setattr(self, k, v)

    def update(self, attr: str, value: AnyStr, *, image=None):
        has_changed = attr in self.__dict__ and getattr(self.attr) != value
        self._db.change_user(self.id, **{attr: value})
        super().__setattr__(attr, value)
        if has_changed:
            self.notify_observers({'attr': attr, 'image': image})        

    def __setattr__(self, attr: str, value: AnyStr):
        raise TypeError((
                "'{}' object has no attribute '__setattr__' method. "
                "Use 'update' instead"
            ).format(self.__class__.__name__))
