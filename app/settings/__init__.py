
from functools import lru_cache
from typing import Dict, Type

from .base import AppEnvTypes, BaseAppSettings
from .development import DevAppSettings
from .production import ProdAppSettings
from .test import TestAppSettings
from .base import AppSettings

environments: Dict[AppEnvTypes, Type[AppSettings]] = {
    AppEnvTypes.dev: DevAppSettings,
    AppEnvTypes.prod: AppSettings,
    AppEnvTypes.test: TestAppSettings,
}

app_env: str = BaseAppSettings().app_env
settings: AppSettings = environments[app_env]()

def get_app_settings() -> AppSettings:
    return settings