from config import config
from modules.fediway.rankers.kirby import Kirby
from modules.fediway.rankers.stats import SimpleStatsRanker

kirby = Kirby.load(config.fediway.kirby_path)
kirby.set_label_weights(
    {
        "label.is_favourited": config.fediway.kirby_label_weight_is_favourited,
        "label.is_reblogged": config.fediway.kirby_label_weight_is_reblogged,
        "label.is_replied": config.fediway.kirby_label_weight_is_replied,
        "label.is_reply_engaged_by_author": config.fediway.kirby_label_weight_is_reply_engaged_by_author,
    }
)

stats_ranker = SimpleStatsRanker(decay_rate=config.fediway.feed_decay_rate)
