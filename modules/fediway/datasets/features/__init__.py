
from .status import (
    NumGifs, 
    NumImages, 
    NumVideos,
    NumTags,
    NumMentions,
    NumFavourites,
    NumReblogs,
    NumReplies,
    AgeInSeconds,
)

from .interactions import (
    HasReplied,
    HasFavourited,
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
        NumFavourites,
        NumReblogs,
        NumReplies,
        AgeInSeconds,
    ]
} | {
    f'interactions.{f.__featname__}': f for f in [
        HasReplied,
        HasFavourited,
        NumFavouritesA2B,
        NumFavouritesB2A
    ]
}