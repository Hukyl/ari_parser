import abc
import sqlite3
import threading
from datetime import datetime
from typing import Union

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


class AbstractDatabaseMeta(Singleton, abc.ABCMeta):
    pass


class AbstractDatabase(abc.ABC, metaclass=AbstractDatabaseMeta):
    def __init__(self, *, db_name:str=None):
        self.db_name = db_name or settings.DB_NAME
        self.setup_db()

    @staticmethod
    def dict_factory(cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    @abc.abstractmethod
    def setup_db(self):
        pass

    def execute(self, sql, params=tuple()) -> list[dict]:
        with threading.Lock():
            with sqlite3.connect(
                        self.db_name, detect_types=sqlite3.PARSE_DECLTYPES
                    ) as conn:
                conn.row_factory = self.dict_factory
                return conn.execute(sql, params).fetchall()


class ChatDatabase(AbstractDatabase):
    def setup_db(self):
        self.execute(
            '''CREATE TABLE IF NOT EXISTS chats( 
                id INTEGER NOT NULL,
                is_subscribed BOOLEAN DEFAULT 1,
                UNIQUE(id) ON CONFLICT REPLACE
            )'''
        )

    def add_chat(self, chat_id:int, is_subscribed:bool=True) -> bool:
        if not self.check_chat_exists(chat_id):
            self.execute(
                "INSERT INTO chats VALUES (?, ?)",
                (chat_id, is_subscribed)
            )
            return True
        return False

    def check_chat_exists(self, chat_id: int) -> bool:
        return len(
            self.execute('SELECT id FROM chats WHERE id = ?', (chat_id,))
        ) > 0

    def subscribe(self, chat_id: int) -> bool:
        if self.check_chat_exists(chat_id):
            self.execute(
                "UPDATE chats SET is_subscribed = 1 WHERE id = ?", 
                (chat_id, )
            )            
        else:
            self.add_chat(chat_id, is_subscribed=True)
        return True

    def unsubscribe(self, chat_id: int) -> bool:
        if self.check_chat_exists(chat_id):
            self.execute(
                "UPDATE chats SET is_subscribed = 0 WHERE id = ?", 
                (chat_id, )
            )
        else:
            self.add_chat(chat_id, is_subscribed=False)
        return True

    def is_subscribed(self, chat_id:int) -> bool:
        if self.check_chat_exists(chat_id):
            return self.execute(
                'SELECT is_subscribed FROM chats WHERE id = ?', (chat_id, )
            )[0]['is_subscribed']
        return False

    def get_subscribed_chats(self):
        return [
            data['id'] for data in self.execute(
                'SELECT id FROM chats WHERE is_subscribed = 1'
            )
        ]


class AccountDatabase(AbstractDatabase):
    def setup_db(self):
        self.execute(
            '''CREATE TABLE IF NOT EXISTS accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                email VARCHAR UNIQUE,
                password VARCHAR,
                auth_token VARCHAR DEFAULT NULL,
                session_id VARCHAR DEFAULT NULL
            )'''
        )
        self.execute(
            '''CREATE TABLE IF NOT EXISTS updates(
                id INTEGER UNIQUE,
                day_offset INTEGER DEFAULT 0,
                status VARCHAR DEFAULT "Unidentified",
                datetime_signed DATETIME DEFAULT NULL,
                office_signed VARCHAR DEFAULT NULL,
                FOREIGN KEY (id) REFERENCES accounts(id)
            )'''
        )
        self.execute(
            '''CREATE TABLE IF NOT EXISTS dependents(
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                owner_id INTEGER,
                name VARCHAR,
                datetime_signed DATETIME DEFAULT NULL,
                office_signed VARCHAR DEFAULT NULL,
                FOREIGN KEY (owner_id) REFERENCES accounts(id),
                UNIQUE (name) ON CONFLICT IGNORE      
            )'''
        )

    def add_account(
                self, email: str, password: str, 
                auth_token: str = None, session_id: str = None
            ) -> Union[bool, int]:
        if not self.check_account_exists(email=email):
            self.execute(
                "INSERT INTO accounts(email, password, auth_token, session_id) \
                 VALUES (?, ?, ?, ?)",
                (email, password, auth_token, session_id)
            )
            account_id = self.execute(
                'SELECT id FROM accounts WHERE email = ?', (email,)
            )[0]['id']
            self.execute("INSERT INTO updates(id) VALUES (?)", (account_id, ))
            return account_id
        raise exceptions.AccountAlreadyExistsException

    def add_dependent(
            self, owner_id: int, name: str, 
            datetime_signed: datetime = None, office_signed: str = None):
        self.execute(
            """INSERT INTO dependents(
                owner_id, name, datetime_signed, office_signed
            ) VALUES (?, ?, ?, ?)""", 
            (owner_id, name, datetime_signed, office_signed)
        )
        return True

    @xor(['account_id', 'email'])
    def get_account(
            self, *, account_id: int = None, email: str = None
        ) -> dict:
        if account_id:
            if not self.check_account_exists(account_id=account_id):
                raise exceptions.AccountDoesNotExistException
            clause, param = "WHERE id = ?", account_id
        else:
            if not self.check_account_exists(email=email):
                raise exceptions.AccountDoesNotExistException
            clause, param = "WHERE email = ?", email
        return self.execute(
            "SELECT * FROM accounts %s" % clause, (param, )
        )[0]

    def get_updates(self, account_id: int) -> dict:
        if self.check_account_exists(account_id=account_id):
            data = self.execute(
                "SELECT * FROM updates WHERE id = ?", (account_id, )
            )[0]
            return data
        raise exceptions.AccountDoesNotExistException

    @xor(['dependent_id', 'dependent_name'])
    def check_dependent_exists(
            self, *, dependent_id: int = None, dependent_name: str = None
        ) -> bool:
        if dependent_id:
            clause, param = 'WHERE id = ?', dependent_id
        else:
            clause, param = 'WHERE name = ?', dependent_name
        return len(
            self.execute(
                'SELECT id FROM dependents %s' % clause, (param,)
            )
        ) > 0

    @xor(['dependent_id', 'dependent_name'])
    def get_dependent(
            self, *, dependent_id: int = None, dependent_name: str = None
        ) -> dict:
        name = 'dependent_id' if dependent_id else 'dependent_name'
        value = dependent_id or dependent_name
        if self.check_dependent_exists(**{name: value}):
            clause = 'WHERE {} = ?'.format('id' if dependent_id else 'name') 
            param = dependent_id or dependent_name
            data = self.execute(
                'SELECT * FROM dependents %s' % clause, (param, )
            )[0]
            return data
        raise exceptions.DependentDoesNotExistException

    def get_dependents(self, account_id: int) -> list[int]:
        if self.check_account_exists(account_id=account_id):
            return [
                data['name'] for data in self.execute(
                    'SELECT name FROM dependents WHERE owner_id = ?', 
                    (account_id, )
                )
            ]
        raise exceptions.AccountDoesNotExistException

    @xor(['account_id', 'email'])
    def check_account_exists(
            self, *, account_id: int = None, email: str = None
        ) -> bool:
        if account_id:
            query = self.execute(
                'SELECT id FROM accounts WHERE id = ?', (account_id, )
            )
        else:
            query = self.execute(
                'SELECT id FROM accounts WHERE email = ?', (email, )
            )
        return len(query) > 0

    def change_account(self, account_id: int, **kwargs):
        if self.check_account_exists(account_id=account_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE accounts SET %s = ? WHERE id = ?' % k,
                        (v, account_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.AccountDoesNotExistError

    def change_update(self, account_id: int, **kwargs):
        if self.check_account_exists(account_id=account_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE updates SET %s = ? WHERE id = ?' % k,
                        (v, account_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.AccountDoesNotExistError

    def change_dependent(self, dependent_id: int, **kwargs):
        if self.check_dependent_exists(dependent_id=dependent_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE dependents SET %s = ? WHERE id = ?' % k,
                        (v, dependent_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.DependentDoesNotExistException
