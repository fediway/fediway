
from app.modules.models import Account

class AccountEventsHandler():
    def __init__(self):
        pass

    def parse(self, payload: dict) -> Account:
        return Account(**payload)

    def created(self, account):
        pass

    def updated(self, old: Account, new: Account):
        pass