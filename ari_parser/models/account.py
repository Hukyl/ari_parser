from typing import AnyStr, Any

from .db import AccountDatabase
from . import Observable


class Account:
    _db = AccountDatabase()

    def __init__(self, email: str):
        data = self._db.get_account(email=email)
        for k, v in data.items():
            self.__dict__[k] = v
        self.__dict__['updates'] = Updates(self)

    @property
    def dependents(self):
        return [Dependent(id_, self) for id_ in self._db.get_dependents()]

    @property
    def is_signed(self):
        return self.updates.datetime_signed and self.updates.office_signed

    def add_dependent(self, *args, **kwargs):
        self._db.add_dependent(self.id, *args, **kwargs)

    @classmethod
    def create_account(cls, *args, **kwargs):
        cls._db.add_account(*args, **kwargs)

    @classmethod
    def exists(cls, email: str):
        return cls._db.check_email_exists(email)

    def __setattr__(self, attr: str, value: Any):
        self._db.change_account(self.id, **{attr: value})
        super().__setattr__(attr, value)


class Updates(Observable):
    _db = AccountDatabase()

    def __init__(self, owner: Account):
        super().__init__()
        super().__setattr__('owner', owner)
        for k, v in self._db.get_updates(owner.id).items():
            super().__setattr__(k, v)

    def update(self, attrs: dict[str, Any], *, additional: dict = None):
        if additional is None:
            additional = dict()
        additional.pop('attrs', None)
        for k, v in attrs.items():
            setattr(self, k, v)
        self.notify_observers(attrs, additional=additional)        

    def __setattr__(self, attr: str, value: AnyStr):
        self._db.change_update(self.owner.id, **{attr: value})
        super().__setattr__(attr, value)


class Dependent:
    _db = AccountDatabase()

    def __init__(self, id_: int, owner: Account):
        self.__dict__['owner'] = owner
        for k, v in self._db.get_dependent(id_):
            self.__dict__[k] = v

    def __setattr__(self, attr: str, value: Any):
        self._db.change_dependent(self.id, **{attr: value})
        super().__setattr__(attr, value)

    @property
    def is_signed(self):
        return self.datetime_signed and self.office_signed
