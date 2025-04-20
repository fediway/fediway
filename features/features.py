
from feast import FeatureView, Field, FileSource, PushSource, FeatureService
from feast.data_format import JsonFormat
from feast.types import Int64
from datetime import timedelta

from entities import account, author
from data_sources import account_author_push_source
from utils import flatten

author_features = []
account_features = []
account_author_features = []
GROUPS = [
    ('account', [account], ['1d', '7d', '30d']),
    ('author', [author], ['1d', '7d', '30d']),
    ('account_author', [account, author], ['30d']),
]
FEATURES = [
    {
        'name': 'engagement',
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
        'name': 'engagement_is',
        'types': ['favourite', 'reblog', 'reply'],
        'fields': [
            'num_images', 
            'num_gifvs', 
            'num_videos', 
            'num_audios'
        ],
    },
    {
        'name': 'engagement_has',
        'types': ['image', 'gifv', 'video'],
        'fields': [
            'fav_count', 
            'reblogs_count', 
            'replies_count'
        ],
    },
]

schema = []

for group, group_entities, specs in GROUPS:
    for feats in FEATURES:
        for t in feats['types']:

            fv_name = f"{group}_{feats['name']}_{t}"
            schema = flatten([[
                Field(name=f"{fv_name}.{name}_{spec}", dtype=Int64) for name in feats['fields']
            ] for spec in specs])
            _fv = FeatureView(
                name=fv_name,
                entities=group_entities,
                ttl=timedelta(days=365),
                schema=schema,
                online=True, 
                source=PushSource(
                    name=f"{fv_name}_features",
                    batch_source=FileSource(
                        name=f"{fv_name}_source",
                        path=f"../data/{fv_name}.parquet",
                        timestamp_field="event_time",
                    ),
                )
            )

            if group == 'account':
                account_features.append(_fv)
            if group == 'author':
                author_features.append(_fv)
            if group == 'account_author':
                account_author_features.append(_fv)
            
            globals()[_fv.name] = _fv
