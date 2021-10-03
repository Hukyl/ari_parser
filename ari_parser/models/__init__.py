from abc import ABC
from typing import Callable


class Observable(ABC):
    def __init__(self):
        super().__setattr__('observers', [])

    def add_observer(self, obs: Callable):
        self.observers.append(obs)

    def remove_observer(self, obs: Callable):
        self.observers.remove(obs)

    def notify_observers(self, *args, **kwargs):
        for observer in self.observers:
            observer(self, *args, **kwargs)
