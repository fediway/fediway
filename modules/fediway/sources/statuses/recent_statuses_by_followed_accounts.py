from sqlmodel import text, Session
from collections import deque

from ..base import Source


class RecentStatusesByFollowedAccounts(Source):
    def __init__(self, db: Session, account_id, latest_n_per_account: int = 10):
        self.db = db
        self.account_id = account_id
        self.latest_n_per_account = latest_n_per_account

    def query(self, limit: int):
        return text(f"""
        SELECT 
            f.target_account_id,
            s.id            AS status_id
        FROM follows AS f
        JOIN LATERAL (
            SELECT s.id
            FROM statuses s
            WHERE s.account_id = f.target_account_id 
              AND s.in_reply_to_id IS NULL
            ORDER BY s.created_at DESC
            LIMIT {self.latest_n_per_account}
        ) AS s ON true
        WHERE f.account_id = {self.account_id}
        LIMIT {limit};
        """)

    def collect(self, limit: int):
        account_statuses = {}

        for account_id, status_id in self.db.exec(self.query(limit)).all():
            account_statuses.setdefault(account_id, deque()).append(status_id)

        while account_statuses:
            for acct in list(account_statuses):
                queue = account_statuses[acct]

                yield queue.popleft()

                if not queue:
                    del account_statuses[acct]
