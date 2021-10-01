from .db import ChatDatabase


class Chat:
    _db = ChatDatabase()

    def __init__(self, chat_id: int):
        self.id = chat_id

    @property
    def is_subscribed(self):
        return self._db.is_subscribed(self.id)

    def subscribe(self):
        self._db.subscribe(self.id)

    def unsubscribe(self):
        self._db.unsubscribe(self.id)

    @classmethod
    def get_subscribed(cls):
        for chat_id in cls._db.get_subscribed_chats():
            yield cls(chat_id)
