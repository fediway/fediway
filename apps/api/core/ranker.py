from config import config
from modules.fediway.rankers.stats import SimpleStatsRanker

stats_ranker = SimpleStatsRanker(decay_rate=config.fediway.feed_decay_rate)
