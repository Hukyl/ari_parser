from typing import AnyStr, Any

from .db import UserDatabase
from . import Observable


class User:
    _db = UserDatabase()

    def __init__(self, email: str):
        data = self._db.get_user(email=email)
        for k, v in data.items():
            self.__dict__[k] = v
        self.__dict__['updates'] = Updates(self)

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
        super().__setattr__('owner', owner)
        for k, v in self._db.get_updates(owner.id).items():
            super().__setattr__(k, v)

    def update(self, attr: str, value: AnyStr, *, image=None):
        has_changed = attr in self.__dict__ and getattr(self, attr) != value
        setattr(self, attr, value)
        if has_changed:
            self.notify_observers({'attr': attr, 'image': image})        

    def __setattr__(self, attr: str, value: AnyStr):
        self._db.change_update(self.owner.id, **{attr: value})
        super().__setattr__(attr, value)
