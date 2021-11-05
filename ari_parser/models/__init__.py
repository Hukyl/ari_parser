from abc import ABC
from typing import Any


class Observable(ABC):
    def __init__(self):
        self.observers = []

    def add_observer(self, obs: 'Observer'):
        self.observers.append(obs)

    def remove_observer(self, obs: 'Observer'):
        self.observers.remove(obs)

    def notify_observers(self, *, additional: dict = None, **kwargs):
        if additional is None:
            additional = dict()
        for observer in self.observers:
            observer.update(self, kwargs, additional=additional)


class Observer(ABC):
    def update(
                self, observable: Observable, attrs: dict[str, Any], 
                *, additional: dict[str, Any]
            ):
        pass
