
from modules.fediway.rankers.stats import SimpleStatsRanker

from config import config

ranker = SimpleStatsRanker(
    decay=config.fediway.feed_decay_rate
)