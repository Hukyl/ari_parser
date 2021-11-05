import abc
import sqlite3
import threading
from typing import Any, Union
from datetime import datetime
import pickle

import settings
from . import exceptions
from utils import Singleton, xor


sqlite3.register_adapter(
    datetime, lambda x: x.strftime('%Y-%m-%d %H:%M').encode('ascii')
)
sqlite3.register_converter(
    "datetime", 
    lambda x: datetime.strptime(x.decode("ascii"), '%Y-%m-%d %H:%M')
)
sqlite3.register_adapter(list, lambda x: pickle.dumps(x))
sqlite3.register_converter("list", lambda x: pickle.loads(x))


class AbstractDatabaseMeta(Singleton, abc.ABCMeta):
    pass


class AbstractDatabase(abc.ABC, metaclass=AbstractDatabaseMeta):
    def __init__(self, *, db_name: str = None):
        self.db_name = db_name or settings.DB_NAME
        self.setup_db()

    @staticmethod
    def dict_factory(cursor: sqlite3.Cursor, row: list[Any]) -> dict[str, Any]:
        """
        Function for sqlite3.Connection.row_factory
        
        Args:
            cursor (sqlite3.Cursor): cursor containing column names
            row (list[Any]): data of database query
        
        Returns:
            dict[str, Any]
        """
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    @abc.abstractmethod
    def setup_db(self) -> None:
        """
        Setup database's tables
        """
        pass

    def execute(
                self, sql: str, params: Union[dict[str, Any], tuple[...]] = (),
                *, as_default: bool = False
            ) -> Union[list[dict[str, Any]], sqlite3.Cursor]:
        """
        Execute sql query. Is thread-safe.
        
        Args:
            sql (str): SQL query
            params (Union[dict[str, Any], tuple[...]], optional): parameter 
                substitution
            as_default (bool, optional): to return the default
                sqlite3.Cursor object
        
        Returns:
            Union[list[dict[str, Any]], sqlite3.Cursor]
        """
        with threading.Lock():
            with sqlite3.connect(
                        self.db_name, detect_types=sqlite3.PARSE_DECLTYPES
                    ) as conn:
                conn.row_factory = self.dict_factory
                query = conn.execute(sql, params)
                if not as_default:
                    return query.fetchall()
                return query


class ChatDatabase(AbstractDatabase):
    def setup_db(self):
        self.execute('''CREATE TABLE IF NOT EXISTS chats( 
            id INTEGER NOT NULL,
            is_subscribed BOOLEAN DEFAULT 1,
            UNIQUE(id) ON CONFLICT REPLACE
        )''')

    def add_chat(self, chat_id: int, is_subscribed: bool = True) -> bool:
        """
        Add chat to database.
        
        Args:
            chat_id (int): chat's id
            is_subscribed (bool, optional): is chat subscribed to notifications
        
        Returns:
            bool: was the chat added successfully
        """
        if not self.check_chat_exists(chat_id):
            self.execute(
                "INSERT INTO chats VALUES (?, ?)",
                (chat_id, is_subscribed)
            )
            return True
        return False

    def check_chat_exists(self, chat_id: int) -> bool:
        """
        Check if chat exists in database.
        
        Args:
            chat_id (int): chat's id
        
        Returns:
            bool
        """
        return len(
            self.execute('SELECT id FROM chats WHERE id = ?', (chat_id,))
        ) > 0

    def subscribe(self, chat_id: int) -> True:
        """
        Subscribe chat to notifications.
        If chat does not exist in databse, it is created.
        
        Args:
            chat_id (int): chat's id to subscribe
        
        Returns:
            True
        """
        if self.check_chat_exists(chat_id):
            self.execute(
                "UPDATE chats SET is_subscribed = 1 WHERE id = ?", 
                (chat_id, )
            )            
        else:
            self.add_chat(chat_id, is_subscribed=True)
        return True

    def unsubscribe(self, chat_id: int) -> True:
        """
        Unsubscribe chat from notifications.
        If chat does not exist in database, it is created.
        Opposite of `subscribe()`.
        
        Args:
            chat_id (int): chat's id to unsubscribe
        
        Returns:
            True
        """
        if self.check_chat_exists(chat_id):
            self.execute(
                "UPDATE chats SET is_subscribed = 0 WHERE id = ?", 
                (chat_id, )
            )
        else:
            self.add_chat(chat_id, is_subscribed=False)
        return True

    def is_subscribed(self, chat_id: int) -> bool:
        """
        Check if chat is subscribed.
        If chat does not exist, return False.
        
        Args:
            chat_id (int): chat's id to check
        
        Returns:
            bool
        """
        if self.check_chat_exists(chat_id):
            return self.execute(
                'SELECT is_subscribed FROM chats WHERE id = ?', (chat_id, )
            )[0]['is_subscribed']
        return False

    def get_subscribed_chats(self) -> int:
        """
        Get subscribed chats' ids.

        Yields:
            int: Description
        """
        for data in self.execute(
                    'SELECT id FROM chats WHERE is_subscribed = 1', 
                    as_default=True
                ):
            yield data['id']


class AccountDatabase(AbstractDatabase):
    def setup_db(self):
        self.execute('''CREATE TABLE IF NOT EXISTS account(
            id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            email VARCHAR UNIQUE,
            password VARCHAR,
            auth_token VARCHAR DEFAULT NULL,
            session_id VARCHAR DEFAULT NULL,
            day_offset INTEGER DEFAULT 0,
            unavailability_datetime LIST DEFAULT NULL,
            update_id INTEGER UNIQUE,
            FOREIGN KEY (update_id) REFERENCES updates(id)
        )''')
        self.execute('''CREATE TABLE IF NOT EXISTS updates(
            id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            status VARCHAR DEFAULT "Unidentified",
            datetime_signed DATETIME DEFAULT NULL,
            office_signed VARCHAR DEFAULT NULL
        )''')
        self.execute('''CREATE TABLE IF NOT EXISTS dependent(
            id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            owner_id INTEGER,
            name VARCHAR UNIQUE,
            update_id INTEGER UNIQUE,
            FOREIGN KEY (update_id) REFERENCES updates(id),
            FOREIGN KEY (owner_id) REFERENCES account(id)
        )''')

    def add_account(self, email: str, password: str) -> int:
        """
        Add account to database.
        Passwords are stored in plain text.
        
        Args:
            email (str): account's email
            password (str): account's password
        
        Returns:
            int: account's id in database
        
        Raises:
            exceptions.AccountAlreadyExistsException: 
                account with this email already exists
        """
        if not self.check_account_exists(email=email):
            update_id = self.execute(
                "INSERT INTO updates DEFAULT VALUES", as_default=True
            ).lastrowid
            account_id = self.execute(
                "INSERT INTO account(email, password, update_id) \
                 VALUES (?, ?, ?)",
                (email, password, update_id), as_default=True
            ).lastrowid
            return account_id
        raise exceptions.AccountAlreadyExistsException

    def add_dependent(self, owner_id: int, name: str) -> int:
        """
        Add dependent to the database
        
        Args:
            owner_id (int): account-owner's id 
            name (str): dependent's name
        
        Returns:
            int: dependent's id in database
        
        Raises:
            exceptions.DependentAlreadyExistsException:
                if dependent with this name already exists
        """
        if not self.check_dependent_exists(dependent_name=name):
            update_id = self.execute(
                "INSERT INTO updates DEFAULT VALUES", as_default=True
            ).lastrowid
            return self.execute(
                """INSERT INTO dependent(
                    owner_id, name, update_id
                ) VALUES (?, ?, ?)""", (owner_id, name, update_id),
                as_default=True
            ).lastrowid
        raise exceptions.DependentAlreadyExistsException

    @xor(['account_id', 'email'])
    def get_account(
                self, *, account_id: int = None, email: str = None
            ) -> dict[str, Any]:
        """
        Get account data by its identifiers.
        One and only one of the arguments must be passed.
        
        Args:
            account_id (int, optional): account's id
            email (str, optional): account's email
        
        Returns:
            dict[str, Any]
        
        Raises:
            exceptions.AccountDoesNotExistException: 
                if account with these identifiers does not exist
        """
        if account_id:
            if not self.check_account_exists(account_id=account_id):
                raise exceptions.AccountDoesNotExistException
            clause, param = "WHERE id = ?", account_id
        else:
            if not self.check_account_exists(email=email):
                raise exceptions.AccountDoesNotExistException
            clause, param = "WHERE email = ?", email
        return self.execute(
            "SELECT * FROM account %s" % clause, (param, )
        )[0]

    def get_updates(self, update_id: int) -> dict[str, Any]:
        """
        Get update's data by its id.
        
        Args:
            update_id (int): update's id
        
        Returns:
            dict[str, Any]: data of update
        
        Raises:
            exceptions.UpdatesDoNotExistException: 
                if update with this id does not exist
        """
        if self.check_updates_exist(update_id):
            return self.execute(
                "SELECT * FROM updates WHERE id = ?", (update_id, )
            )[0]
        raise exceptions.UpdatesDoNotExistException

    @xor(['dependent_id', 'dependent_name'])
    def check_dependent_exists(
                self, *, dependent_id: int = None, dependent_name: str = None
            ) -> bool:
        """
        Check if dependent exists.
        One and only one of the arguments must be passed
        
        Args:
            dependent_id (int, optional): dependent's id
            dependent_name (str, optional): dependent's name
        
        Returns:
            bool
        """
        if dependent_id:
            clause, param = 'WHERE id = ?', dependent_id
        else:
            clause, param = 'WHERE name = ?', dependent_name
        return len(
            self.execute(
                'SELECT id FROM dependent %s' % clause, (param,)
            )
        ) > 0

    def check_updates_exist(self, update_id: int) -> bool:
        """
        Check if updates exist.
        
        Args:
            update_id (int): update's id
        
        Returns:
            bool
        """
        return len(
            self.execute('SELECT id FROM updates WHERE id = ?', (update_id, ))
        ) > 0

    @xor(['dependent_id', 'dependent_name'])
    def get_dependent(
                self, *, dependent_id: int = None, dependent_name: str = None
            ) -> dict[str, Any]:
        """
        Get data of the dependent.
        One and only one of the arguments must be passed
        
        Args:
            dependent_id (int, optional): dependent id
            dependent_name (str, optional): dependent name
        
        Returns:
            dict[str, Any]: data of dependent
        
        Raises:
            exceptions.DependentDoesNotExistException: Description
        """
        name = 'dependent_id' if dependent_id else 'dependent_name'
        value = dependent_id or dependent_name
        if self.check_dependent_exists(**{name: value}):
            clause = 'WHERE {} = ?'.format('id' if dependent_id else 'name') 
            param = dependent_id or dependent_name
            data = self.execute(
                'SELECT * FROM dependent %s' % clause, (param, )
            )[0]
            return data
        raise exceptions.DependentDoesNotExistException

    def get_dependents(self, account_id: int) -> list[str]:
        """
        Get dependent names of particular account
        
        Args:
            account_id (int): account id
        
        Returns:
            list[str]: names of dependents
        
        Raises:
            exceptions.AccountDoesNotExistException: 
                if account with this id does not exist
        """
        if self.check_account_exists(account_id=account_id):
            return [
                data['name'] for data in self.execute(
                    'SELECT name FROM dependent WHERE owner_id = ?', 
                    (account_id, )
                )
            ]
        raise exceptions.AccountDoesNotExistException

    @xor(['account_id', 'email'])
    def check_account_exists(
                self, *, account_id: int = None, email: str = None
            ) -> bool:
        """
        Check whether the account exists.
        One and only one argument must be passed
        
        Args:
            account_id (int, optional): account id
            email (str, optional): account email
        
        Returns:
            bool: if account exists
        """
        if account_id:
            query = self.execute(
                'SELECT id FROM account WHERE id = ?', (account_id, )
            )
        else:
            query = self.execute(
                'SELECT id FROM account WHERE email = ?', (email, )
            )
        return len(query) > 0

    def change_account(self, account_id: int, **kwargs) -> True:
        """
        Change account's data in database
        
        Args:
            account_id (int): account id
            **kwargs: fields to be changed
        
        Returns:
            True
        
        Raises:
            exceptions.AccountDoesNotExistException: 
                if account with this id does not exist
            KeyError: invalid field name
            ValueError: invalid field value
        """
        if self.check_account_exists(account_id=account_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE account SET %s = ? WHERE id = ?' % k,
                        (v, account_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.AccountDoesNotExistException

    def change_update(self, update_id: int, **kwargs) -> True:
        """
        Change update's data in database
        
        Args:
            update_id (int): update's id
            **kwargs: fields to be changed
        
        Returns:
            True
        
        Raises:
            exceptions.UpdatesDoNotExistException: 
                if update with this id does not exist
            KeyError: invalid field name
            ValueError: invalid field value
        """
        if self.check_updates_exist(update_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE updates SET %s = ? WHERE id = ?' % k,
                        (v, update_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.UpdatesDoNotExistException

    def change_dependent(self, dependent_id: int, **kwargs) -> True:
        """
        Change data of dependent in database
        
        Args:
            dependent_id (int): id of dependent to change
            **kwargs: fields to change
        
        Returns:
            True
        
        Raises:
            exceptions.DependentDoesNotExistException: 
                if dependent with this id does not exist
            KeyError: Invalid field name
            ValueError: Invalid field value
        """
        if self.check_dependent_exists(dependent_id=dependent_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE dependent SET %s = ? WHERE id = ?' % k,
                        (v, dependent_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.DependentDoesNotExistException
