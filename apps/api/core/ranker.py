from config import config
from modules.fediway.rankers.stats import SimpleStatsRanker

ranker = SimpleStatsRanker(decay=config.fediway.feed_decay_rate)
