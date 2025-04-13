
from .status import (
    NumGifs, 
    NumImages, 
    NumVideos,
    NumTags,
    NumMentions,
    AgeInSeconds
)

from .interactions import (
    ARepliedB,
    BRepliedA,
    NumFavouritesA2B,
    NumFavouritesB2A,
)

FEATURES = {
    f'status.{f.__featname__}': f for f in [
        NumGifs, 
        NumImages, 
        NumVideos,
        NumTags,
        NumMentions,
        AgeInSeconds
    ]
} | {
    f'interactions.{f.__featname__}': f for f in [
        ARepliedB,
        BRepliedA,
        NumFavouritesA2B,
        NumFavouritesB2A
    ]
}