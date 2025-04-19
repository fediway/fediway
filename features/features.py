
from feast import FeatureView, Field, FileSource, PushSource, FeatureService
from feast.data_format import JsonFormat
from feast.types import Int64
from datetime import timedelta

from entities import account, author
from data_sources import account_author_push_source
from utils import flatten

account_author_view = FeatureView(
    name="account_author_features",
    entities=[account, author],
    ttl=timedelta(days=365),
    schema=[
        Field(name="fav_count_7d", dtype=Int64),
        Field(name="reblogs_count_7d", dtype=Int64),
        Field(name="replies_count_7d", dtype=Int64),
        Field(name="fav_count_30d", dtype=Int64),
        Field(name="reblogs_count_30d", dtype=Int64),
        Field(name="replies_count_30d", dtype=Int64),
    ],
    online=True, 
    source=account_author_push_source
)

# --- author features ---

author_features = []
SPECS = ['1d', '7d', '30d']
AUTHOR_FEATURES = [
    {
        'name': 'author_engagement',
        'types': ['all'],
        'fields': [
            'fav_count', 
            'reblogs_count', 
            'replies_count', 
            'num_images', 
            'num_gifvs', 
            'num_videos', 
            'num_audios'
        ],
    },
    {
        'name': 'author_engagement_is',
        'types': ['favourite', 'reblog', 'reply'],
        'fields': [
            'num_images', 
            'num_gifvs', 
            'num_videos', 
            'num_audios'
        ],
    },
    {
        'name': 'author_engagement_has',
        'types': ['image', 'gifv', 'video'],
        'fields': [
            'fav_count', 
            'reblogs_count', 
            'replies_count'
        ],
    },
]

schema = []

for group in AUTHOR_FEATURES:
    for t in group['types']:
        fv_name = f"{group['name']}_{t}"
        schema += flatten([
            [
                Field(name=f"{fv_name}_{name}_{spec}", dtype=Int64) for name in group['fields']
            ] for spec in SPECS
        ])
        # fv_name = f"{group['name']}_{t}"
        # author_features.append(FeatureView(
        #     name=f"{fv_name}_features",
        #     entities=[author],
        #     ttl=timedelta(days=365),
        #     schema=flatten([
        #         [
        #             Field(name=f"{fv_name}.{name}_{spec}", dtype=Int64) for name in group['fields']
        #         ] for spec in SPECS
        #     ]),
        #     online=True, 
        #     source=PushSource(
        #         name=f"{fv_name}_features",
        #         batch_source=FileSource(
        #             name=f"{fv_name}_source",
        #             path=f"../data/{fv_name}.parquet",
        #             timestamp_field="event_time",
        #         ),
        #     )
        # ))
        # print(author_features[-1].name, author_features[-1].schema)
        # globals()[author_features[-1].name] = author_features[-1]

author_features = FeatureView(
    name=f"author_features",
    entities=[author],
    ttl=timedelta(days=365),
    schema=schema,
    online=True, 
    source=PushSource(
        name=f"author_features",
        batch_source=FileSource(
            name=f"author_source",
            path=f"../data/author.parquet",
            timestamp_field="event_time",
        ),
    )
)

for field in author_features.schema:
    print(field.name)
    # author_engagement_all.fav_count_1d

# author_engagement_has_video.fav_count_1d
# author_engagement_has_video.fav_count_1d