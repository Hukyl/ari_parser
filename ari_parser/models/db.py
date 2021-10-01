import abc
import sqlite3
import threading
from typing import Union

import settings
from . import exceptions
from utils import Singleton


class AbstractDatabaseMeta(Singleton, abc.ABCMeta):
    pass


class AbstractDatabase(abc.ABC, metaclass=AbstractDatabaseMeta):
    def __init__(self, *, db_name:str=None):
        self.DB_NAME = db_name or settings.DB_NAME
        self.setup_db()

    @staticmethod
    def dict_factory(cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    @abc.abstractmethod
    def setup_db(self):
        pass

    def execute(self, sql, params=tuple()):
        with threading.Lock():
            with sqlite3.connect(
                        self.DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES
                    ) as conn:
                conn.row_factory = self.dict_factory
                return conn.execute(sql, params).fetchall()


class ChatDatabase(AbstractDatabase):
    def setup_db(self):
        self.execute(
            '''CREATE TABLE IF NOT EXISTS chats( 
                id INTEGER NOT NULL,
                is_subscribed BOOLEAN DEFAULT 1
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


class UserDatabase(AbstractDatabase):
    def setup_db(self):
        self.execute(
            '''CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                email VARCHAR UNIQUE,
                password VARCHAR,
                session VARCHAR DEFAULT NULL
            )'''
        )
        self.execute(
            '''CREATE TABLE IF NOT EXISTS updates(
                id INTEGER UNIQUE,
                status VARCHAR DEFAULT "Unidentified",
                FOREIGN KEY (id) REFERENCES users(id)
            )'''
        )

    def add_user(
                self, email: str, password: str, session:str=None
            ) -> Union[bool, int]:
        if not self.check_email_exists(email):
            self.execute(
                "INSERT INTO users(email, password, session) VALUES (?, ?, ?)",
                (email, password, session)
            )
            user_id = self.execute(
                'SELECT id FROM users WHERE email = ?', (email,)
            )[0]['id']
            self.execute("INSERT INTO updates(id) VALUES (?)", (user_id, ))
            return user_id
        raise exceptions.UserAlreadyExistsException

    def get_user(self, *, user_id:int=None, email:str=None) -> dict:
        if not (user_id or email):
            raise ValueError('either user_id or email must be passed')
        if user_id:
            if not self.check_user_exists(user_id):
                raise exceptions.UserDoesNotExistException
            clause, param = "WHERE id = ?", user_id
        else:
            if not self.check_email_exists(email):
                raise exceptions.UserDoesNotExistException
            clause, param = "WHERE email = ?", email
        return self.execute("SELECT * FROM users %s" % clause, (param, ))[0]

    def get_updates(self, user_id: int) -> dict:
        if self.check_user_exists(user_id):
            data = self.execute(
                "SELECT * FROM updates WHERE id = ?", (user_id, )
            )
            data.pop('id')
            return data
        raise exceptions.UserDoesNotExistException

    def check_email_exists(self, email: str) -> bool:
        return len(
            self.execute('SELECT email FROM users WHERE email = ?', (email,))
        ) > 0

    def check_user_exists(self, user_id:int) -> bool:
        return len(
            self.execute(
                'SELECT id FROM users WHERE id = ?', (user_id,)
            )
        ) > 0

    def change_user(self, user_id:int, **kwargs):
        if self.check_user_exists(user_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE users SET %s = ? WHERE id = ?' % k,
                        (v, user_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.UserDoesNotExistError

    def change_update(self, user_id:int, **kwargs):
        if self.check_user_exists(user_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE updates SET %s = ? WHERE id = ?' % k,
                        (v, user_id)
                    )
            except sqlite3.OperationalError:
                raise KeyError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.UserDoesNotExistError
