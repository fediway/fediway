
from .status import (
    NumGifs, 
    NumImages, 
    NumVideos,
    NumTags,
    NumMentions,
    AgeInSeconds
)

FEATURES = {
    f'status.{f.__featname__}': f for f in [
        NumGifs, 
        NumImages, 
        NumVideos,
        NumTags,
        NumMentions,
        AgeInSeconds
]} | {
    # f'user.{f.__name__}': 
}