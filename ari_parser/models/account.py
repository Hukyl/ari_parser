from typing import Union

from . import Observable
from .db import AccountDatabase


class Account:
    _db = AccountDatabase()

    def __init__(self, email: str):
        data = self._db.get_account(email=email)
        self.id = data['id']
        self.email = email
        self.password = data['password']
        self.auth_token = data['auth_token']
        self.session_id = data['session_id']
        self.day_offset = data['day_offset']
        self.unavailability_datetime = data['unavailability_datetime']
        self.updates = Updates(data['update_id'], self)
        self.dependents = [
            Dependent(name, self) for name in self._db.get_dependents(self.id)
        ]

    @property
    def is_signed(self) -> bool:
        """
        Check if account has a meeting.
        
        Returns:
            bool: ...
        """
        return bool(
            self.updates.datetime_signed and self.updates.office_signed
        )

    def add_dependent(self, name: str) -> 'Dependent':
        """
        Add dependent to self
        
        Args:
            name (str): Dependent's name
        
        Returns:
            Dependent: Instantiated dependent
        """
        self.dependents.append(dependent := Dependent.create(name, self))
        return dependent

    @classmethod
    def create(cls, *args, **kwargs) -> None:
        cls._db.add_account(*args, **kwargs)

    @classmethod
    def exists(cls, **kwargs):
        return cls._db.check_account_exists(**kwargs)

    def update(self, **kwargs) -> None:
        """
        Update account fields in database and locally
        
        Args:
            **kwargs: fields to be changed
        """
        self._db.change_account(self.id, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self) -> str:
        email = self.email
        password = self.password
        return f"{self.__class__.__name__}({email=}, {password=})"

    def __repr__(self) -> str:
        return f"<{str(self)} at {hex(id(self)).upper()}>"


class Dependent:
    _db = AccountDatabase()

    def __init__(self, name: str, owner: Account):
        data = self._db.get_dependent(dependent_name=name)
        self.id = data['id']
        assert data['owner_id'] == owner.id
        self.owner = owner
        self.name = data['name']
        self.updates = Updates(data['update_id'], self)

    def update(self, **kwargs) -> None:
        """
        Update dependent fields in database and locally
        
        Args:
            **kwargs: fields to be changed
        """    
        self._db.change_dependent(self.id, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def exists(cls, name: str) -> bool:
        """
        Check if dependent exists.
        
        Args:
            name (str): dependents name
        
        Returns:
            bool: ...
        """
        return cls._db.check_dependent_exists(dependent_name=name)

    @classmethod
    def create(cls, name: str, owner: Account) -> 'Dependent':
        """
        Create dependent with owner.
        
        Args:
            name (str): dependent's name
            owner (Account): dependent's owner
        
        Returns:
            Dependent: Instantiated dependent
        """
        cls._db.add_dependent(owner.id, name)
        return cls(name, owner)

    @property
    def is_signed(self) -> bool:
        """
        Check if account has a meeting.
        
        Returns:
            bool: ...
        """        
        return bool(
            self.updates.datetime_signed and self.updates.office_signed
        )

    def __str__(self) -> str:
        owner = self.owner
        name = self.name
        return f"{self.__class__.__name__}({name=}, {owner.email=})"

    def __repr__(self) -> str:
        return f"<{str(self)} at {hex(id(self)).upper()}>"


class Updates(Observable):
    _db = AccountDatabase()

    def __init__(self, id_: int, owner: Union[Account, Dependent]):
        super().__init__()
        self.owner = owner
        data = self._db.get_updates(id_)
        self.id = data['id']
        self.status = data['status']
        self.datetime_signed = data['datetime_signed']
        self.office_signed = data['office_signed']

    def update(self, *, additional: dict = None, **kwargs) -> None:
        """
        Update fields in database and locally.
        Implements Observable interface.
        `additional` will be passed to the observers.
        'to_notify' (bool) can be passed to decide whether to 
            notify the observers.
        
        Args:
            additional (dict, optional): Data to be passed to observers
            **kwargs: Fields to be updated

        Returns:
            None: ...
        """
        if additional is None:
            additional = dict()
        additional.pop('attrs', None)
        additional.setdefault('to_notify', True)
        self._db.change_update(self.id, **kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)
        if additional.pop('to_notify'):
            self.notify_observers(kwargs, additional=additional)

    def __str__(self) -> str:
        owner = self.owner
        return f"{self.__class__.__name__}({owner=!s})"

    def __repr__(self) -> str:
        return f"<{str(self)} at {hex(id(self)).upper()}>"
