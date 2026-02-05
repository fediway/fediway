from typing import ClassVar

import pandas as pd

from shared.utils.strings import camel_to_snake, humanize


class Ranker:
    features: ClassVar[list[str]] = []
    _id: ClassVar[str | None] = None
    _display_name: ClassVar[str | None] = None
    _description: ClassVar[str | None] = None
    _tracked_params: ClassVar[list[str]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Default to empty list if not defined
        if "_tracked_params" not in cls.__dict__:
            cls._tracked_params = []

    @property
    def id(self) -> str:
        if self._id:
            return self._id
        return camel_to_snake(self.__class__.__name__)

    @property
    def display_name(self) -> str:
        if self._display_name:
            return self._display_name
        name = self.__class__.__name__
        for suffix in ("Ranker",):
            name = name.removesuffix(suffix)
        return humanize(camel_to_snake(name))

    @property
    def description(self) -> str | None:
        if self._description:
            return self._description
        if self.__doc__:
            return self.__doc__.strip().split("\n")[0]
        return None

    @property
    def class_path(self) -> str:
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    def get_params(self) -> dict:
        return {k: getattr(self, k) for k in self._tracked_params}

    def predict(self, X: pd.DataFrame):
        raise NotImplementedError
