
from sqlmodel import Session, select

from ..models import Status

class Candidate():
    candidate_id: int
    account_id: int
    source: str
    score: float | None = None

    def __init__(self, 
                 status_id: int, 
                 account_id: int, 
                 source: str):
        self.status_id = status_id
        self.account_id = account_id
        self.source = source