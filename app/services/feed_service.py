
from sqlmodel import Session as DBSession, select
from fastapi import Request, BackgroundTasks, Depends

from app.settings import settings
from app.core.db import get_db_session
from app.modules.session import Session
from app.modules.heuristics import DiversifyAccountsHeuristic
from app.modules.sources import Source
from app.modules.feed import Feed, Candidate
from app.modules.ranking import Ranker
from app.modules.models import Feed as FeedModel, Status, FeedRecommendation

class FeedService():
    feed: Feed | None = None

    def __init__(self, 
                 name: str,
                 light_ranker: Ranker,
                 heavy_ranker: Ranker,
                 session: Session, 
                 db: DBSession,
                 tasks: BackgroundTasks,):
        self.name = name
        self.light_ranker = light_ranker
        self.heavy_ranker = heavy_ranker
        self.session = session
        self.db = db
        self.tasks = tasks
        self.sources = []

    def load_or_create(self):
        self.feed = self.session.get(self.name)

        if self.feed is not None:
            return
        
        feed_model = FeedModel(
            session_id=self.session.id,
            ip=self.session.ipv4_address,
            user_agent=self.session.user_agent,
            name=self.name,
        )
        self.db.add(feed_model)
        self.db.commit()

        self.feed = Feed(
            id=feed_model.id,
            name=self.name,
            max_queue_size=settings.feed_max_heavy_candidates,
            heuristics=[
                DiversifyAccountsHeuristic(penalty=0.01)
            ]
        )

        self.session[self.name] = self.feed

    def set_sources(self, sources: list[Source]):
        self.sources = sources

    def fetch_sources(self):
        candidates = []
        max_n_per_source = settings.feed_max_light_candidates // len(self.sources)

        for source in self.sources:
            candidate_ids = source.collect(max_n_per_source)

            # load account_ids for all candidates
            rows = self.db.exec(
                select(Status.id, Status.account_id).where(Status.id.in_(candidate_ids))
            ).all()
            rows = {row.id: row for row in rows}

            candidates += [Candidate(
                status_id=status_id,
                account_id=rows[status_id].account_id,
                source=str(source),
            ) for status_id in candidate_ids]

        # compute scores 
        scores = self.light_ranker.scores(candidates, self.db)

        for i, score in enumerate(scores):
            candidates[i].score = score

        self.feed.add_candidates('light', candidates)

    def get_recommendations(self, n) -> list[int | str]:
        assert len(self.sources) > 0, "Cannot propose recommendations without sources."

        is_new = self.feed.is_empty()

        if is_new:
            self.fetch_sources()

        samples = self.feed.samples('light', n)

        # save recommendations
        self.db.bulk_save_objects([FeedRecommendation(
            feed_id=self.feed.id,
            status_id=candidate.status_id,
            source=candidate.source,
            score=float(candidate.score),
            adjusted_score=float(adjusted_score),
        ) for candidate, adjusted_score in samples])
        self.db.commit()

        return [candidate.status_id for candidate, _ in samples]

def get_feed_service(name: str):
    def _inject(request: Request, 
                tasks: BackgroundTasks,
                db: Session = Depends(get_db_session)):
        from app.core.feed import light_ranker, heavy_ranker

        return FeedService(
            name=name, 
            light_ranker=light_ranker,
            heavy_ranker=heavy_ranker,
            session=request.state.session, 
            db=db, 
            tasks=tasks)
        
    return _inject