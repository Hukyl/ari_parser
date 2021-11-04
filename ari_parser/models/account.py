from typing import Union

from .db import AccountDatabase
from . import Observable


class Account:
    _db = AccountDatabase()

    def __init__(self, email: str):
        for k, v in self._db.get_account(email=email).items():
            setattr(self, k, v)
        self.updates = Updates(self.update_id, self)
        self.__dependents = []
        del self.update_id

    @property
    def dependents(self):
        if not self.__dependents:
            self.__dependents = [
                Dependent(name, self) 
                for name in self._db.get_dependents(self.id)
            ]
        return self.__dependents

    @property
    def is_signed(self):
        return bool(
            self.updates.datetime_signed and self.updates.office_signed
        )

    def add_dependent(self, name) -> 'Dependent':
        return Dependent.create(name, self)

    @classmethod
    def create(cls, *args, **kwargs):
        cls._db.add_account(*args, **kwargs)

    @classmethod
    def exists(cls, **kwargs):
        return cls._db.check_account_exists(**kwargs)

    def update(self, **kwargs):
        self._db.change_account(self.id, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)


class Dependent:
    _db = AccountDatabase()

    def __init__(self, name: str, owner: Account):
        self.owner = owner
        for k, v in self._db.get_dependent(dependent_name=name).items():
            setattr(self, k, v)
        self.updates = Updates(self.update_id, self)
        del self.owner_id, self.update_id

    def update(self, **kwargs):
        self._db.change_dependent(self.id, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def exists(cls, name):
        return cls._db.check_dependent_exists(dependent_name=name)

    @classmethod
    def create(cls, name: str, owner: Account) -> 'Dependent':
        cls._db.add_dependent(owner.id, name)
        return cls(name, owner)

    @property
    def is_signed(self):
        return bool(
            self.updates.datetime_signed and self.updates.office_signed
        )


class Updates(Observable):
    _db = AccountDatabase()

    def __init__(self, id_: int, owner: Union[Account, Dependent]):
        super().__init__()
        self.owner = owner
        for k, v in self._db.get_updates(id_).items():
            setattr(self, k, v)

    def update(self, *, additional: dict = None, **kwargs):
        if additional is None:
            additional = dict()
        additional.pop('attrs', None)
        additional.setdefault('to_notify', True)
        self._db.change_update(self.id, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)
        if additional.pop('to_notify'):
            self.notify_observers(kwargs, additional=additional)
