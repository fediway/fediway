

from .base import BaseConfig

class FeedConfig(BaseConfig):    
    feed_max_age_in_days: int       = 7
    feed_max_light_candidates: int  = 1000
    feed_max_heavy_candidates: int  = 100
    feed_samples_page_size: int     = 10