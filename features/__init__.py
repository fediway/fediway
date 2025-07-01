from .entities import account, author, status, tag, domain

# from .services.kirby import kirby_features
from .views.status import status_features

# from .views.latest_engaged_statuses import latest_engaged_statuses
from .views.account_author_engagement_features import (
    feature_views as account_author_engagement_features,
)
from .views.account_domain_engagement_features import (
    feature_views as account_domain_engagement_features,
)
from .views.account_engagement_features import (
    feature_views as account_engagement_features,
)
from .views.account_tag_engagement_features import (
    feature_views as account_tag_engagement_features,
)
from .views.author_engagement_features import (
    feature_views as author_engagement_features,
)
from .views.tag_engagement_features import feature_views as tag_engagement_features

ENTITIES = [account, author, status, tag, domain]

FEATURE_VIEWS = (
    # engagement features
    account_author_engagement_features
    + account_domain_engagement_features
    + account_engagement_features
    + account_tag_engagement_features
    + author_engagement_features
    + tag_engagement_features
    # status features
    + [status_features]
)

FEATURES_SERVICES = [
    # kirby_features
]
