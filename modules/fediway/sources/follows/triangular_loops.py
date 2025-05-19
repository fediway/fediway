
from arango.database import StandardDatabase

from ..base import Source

class TriangularLoopsSource(Source):
    '''
    In the follow graph u -> v -> w -> u, whenever there isn't an 
    edge v -> u, the Triangular Loops Candidate Source will suggest 
    u as a potential new follow for v.”
    '''

    def __init__(self, db: StandardDatabase):
        self.db = db
        self.max_age = max_age

    def compute_scores(self):
        pass

    def collect(self, limit: int):
        query = """
        LET follows = "follows"

        FOR u IN accounts /* 1. Start at candidate u */ 
            FOR v IN OUTBOUND u follows /* 2. Follow u -> v */ 
                FOR w IN OUTBOUND v follows /* 3. Follow v -> w */ 

                /* Prevent trivial loops and self-cycles */
                FILTER w._id != u._id

                /* Ensure w -> u exists (close the triangle) */
                FILTER LENGTH(
                    FOR e IN follows
                    FILTER e._from == w._id AND e._to == u._id
                    LIMIT 1
                    RETURN 1
                ) == 1

                /* Exclude if v -> u already exists */
                FILTER LENGTH(
                    FOR e2 IN follows
                    FILTER e2._from == v._id AND e2._to == u._id
                    LIMIT 1
                    RETURN 1
                ) == 0

                /* Emit the triangle (u, v, w) */
                RETURN { source: u._key, via: v._key, target: w._key }
        """

        max_age = int((datetime.now() - self.max_age).timestamp() * 1000)

        with self.driver.session() as session:
            results = session.run(query, language=self.language, limit=limit, max_age=max_age)

            for result in list(results):
                yield result['target']