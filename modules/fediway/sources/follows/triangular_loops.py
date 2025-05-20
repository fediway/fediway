
from arango.database import StandardDatabase

from ..base import Source

class TriangularLoopsSource(Source):
    '''
    In the follow graph u -> v -> w -> u, whenever there isn't an 
    edge v -> u, the Triangular Loops Candidate Source will suggest 
    u as a potential new follow for v.”
    '''

    def __init__(self, db: StandardDatabase, account_id: int):
        self.db = db
        self.account_id = account_id

    def collect(self, limit: int):
        query = """
        LET v = DOCUMENT(@source)
        FOR w IN OUTBOUND v follows
            FOR u IN OUTBOUND w follows
                FILTER u._id != v._id

                /* Ensure u -> v exists (close the triangle) */
                FILTER LENGTH(
                    FOR e IN follows
                    FILTER e._from == u._id AND e._to == v._id
                    LIMIT 1
                    RETURN 1
                ) > 0

                /* Exclude if v -> u already exists */
                FILTER LENGTH(
                FOR e2 IN follows
                    FILTER e2._from == v._id AND e2._to == u._id
                    LIMIT 1
                    RETURN 1
                ) == 0
                
                LIMIT @limit
                RETURN { source: v._key, via: w._key, target: u._key }
        """

        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "limit": limit,
                "source": f"accounts/{self.account_id}"
            }
        )

        for result in cursor:
            yield result['target']