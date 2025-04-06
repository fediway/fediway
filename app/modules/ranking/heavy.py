
'''
Inspiration: https://github.com/twitter/the-algorithm-ml/blob/main/projects/home/recap/README.md
scored_tweets_model_weight_fav: The probability the user will favorite the Tweet.
scored_tweets_model_weight_retweet: The probability the user will Retweet the Tweet.
scored_tweets_model_weight_reply: The probability the user replies to the Tweet.
scored_tweets_model_weight_good_profile_click: The probability the user opens the Tweet author profile and Likes or replies to a Tweet.
scored_tweets_model_weight_video_playback50: The probability (for a video Tweet) that the user will watch at least half of the video.
scored_tweets_model_weight_reply_engaged_by_author: The probability the user replies to the Tweet and this reply is engaged by the Tweet author.
scored_tweets_model_weight_good_click: The probability the user will click into the conversation of this Tweet and reply or Like a Tweet.
scored_tweets_model_weight_good_click_v2: The probability the user will click into the conversation of this Tweet and stay there for at least 2 minutes.
scored_tweets_model_weight_negative_feedback_v2: The probability the user will react negatively (requesting "show less often" on the Tweet or author, block or mute the Tweet author).
scored_tweets_model_weight_report: The probability the user will click Report Tweet.

Feature candidates forw fediway (whether the user has seen the post is known):

- user_favs: The probability the user will favorite the status
- user_reblogs: The probability the user will reblog the status
- user_replies: The probability the user will reply to the status
- user_engages_reply: The probability the user will engage with a reply of the status
- reply_engaged_by_author: The probability the user replies to the status and this reply is engaged by the status author

Feature candidates for unkown information about whether the user has seen the post:

- status_sim: The similarity between the last 100 statuses the user liked and the status
- liked_user_sim: The similarity between the user and the average of all the users the status liked

These scores can be estimated via a machine learning model: the heavy ranker.
https://github.com/rust-ml/linfa

Other method:

Treat the Problem as Implicit Feedback

Instead of framing it as a binary classification problem (like/dislike), model the likelihood of engagement given observed interactions.
'''
