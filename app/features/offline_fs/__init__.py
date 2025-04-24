
import pandas as pd
from feast import FeatureView
from sqlmodel import Session
from sqlalchemy import text

import app.utils as utils

def get_historical_features(entity_table: str, fv: FeatureView, db: Session):
    table = f"offline_fs_{fv.name}_features"

    schema_select_clause = ', '.join([f'f.{f.name}' for f in fv.schema])
    entities_select_clause = ', '.join([f'f.{e}' for e in fv.entities])
    entities_and_clause = ' and '.join([f'f.{e} = ds.{e}' for e in fv.entities])
    query = f"""
    select 
        ds.*,
        latest.event_time as event_time,
        (
            select ARRAY[{schema_select_clause}]
            from {table} f 
            where {entities_and_clause} and f.event_time = latest.event_time
            limit 1
        ) as feats
    from {entity_table} ds
    full outer join (
        select max(f.event_time) as event_time, {entities_select_clause}
        from {table} f 
        join {entity_table} ds
        on {entities_and_clause} and f.event_time < ds.time
        group by {entities_select_clause}
    ) as latest
    on {entities_and_clause.replace('f', 'latest')};
    """
    
    rows = []
    
    for row in db.exec(text(query)).mappings().yield_per(100):
        feats = {f"{fv.name}__{f.name}": value for f, value in zip(fv.schema, row['feats'])}
        entities = {e: row[e] for e in fv.entities}

        rows.append(entities | {
            'event_time': row.event_time,
            'label.is_favourited': row.label,
        } | feats)
    
    return pd.DataFrame(rows)