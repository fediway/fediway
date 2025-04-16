
import typing

class Source():
    def collect(self, limit: int):
        raise NotImplemented

    def __str__(self):
        return str(type(self))