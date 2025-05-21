from config import config
from modules.fediway.rankers.kirby import Kirby
from modules.fediway.rankers.stats import SimpleStatsRanker

kirby = Kirby.load(config.fediway.kirby_path)
stats_ranker = SimpleStatsRanker(decay_rate=config.fediway.feed_decay_rate)
