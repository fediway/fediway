
import pandas as pd
from feast import FeatureView
from sqlmodel import Session, Table, MetaData, BigInteger, DateTime, Column
from sqlalchemy.schema import CreateTable
from sqlalchemy import text
from modules.utils import compile_sql
from tqdm import tqdm

def create_entities_table(name: str, db: Session) -> Table:
    table = Table(name, MetaData(),
        Column('account_id', BigInteger, primary_key=True),
        Column('status_id', BigInteger, primary_key=True),
        Column('author_id', BigInteger, primary_key=True),
        Column('time', DateTime),
    )

    db.exec(text(f"DROP TABLE IF EXISTS {table.name};"))
    db.exec(text(
        compile_sql(CreateTable(table), db.get_bind())
        .replace(" NOT NULL", "")
        .replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
    ))
    db.exec(text(f"DELETE FROM {table.name};"))
    db.commit()

    return table

def _get_historical_features_query(entity_table: str, feature_views: list[FeatureView]) -> str:
    queries = []
    for fv in feature_views:
        table = f"offline_fs_{fv.name}_features"
        schema_select_clause = ', '.join([f'f.{f.name}' for f in fv.schema])
        entities_select_clause = ', '.join([f'f.{e}' for e in fv.entities])
        entities_and_clause = ' AND '.join([f'f.{e} = ds.{e}' for e in fv.entities])
        null_columns = ', '.join([f"NULL AS {_fv.name}" for _fv in feature_views if _fv.name != fv.name])

        fv_select = f"""(
            SELECT ARRAY[{schema_select_clause}]
            FROM {table} f 
            WHERE {entities_and_clause} AND f.event_time = latest.event_time
            LIMIT 1
        )::BIGINT[] AS {fv.name}"""

        columns = []
        for _fv in feature_views:
            if _fv.name == fv.name:
                columns.append(fv_select)
            else:
                columns.append(f"NULL::BIGINT[] AS {_fv.name}")
        columns = ',\n  '.join(columns)        

        query = f"""
        SELECT 
            ds.account_id,
            ds.status_id,
            {columns}
        FROM {entity_table} ds
        JOIN (
            SELECT max(f.event_time) AS event_time, {entities_select_clause}
            FROM {table} f 
            JOIN {entity_table} ds
            ON {entities_and_clause} AND f.event_time < ds.time
            GROUP BY {entities_select_clause}
        ) AS latest
        ON {entities_and_clause.replace('f', 'latest')}
        """
        queries.append(query)

    entities_and_clause = ' AND '.join([f'data.{e} = ds.{e}' for e in ['account_id', 'status_id']])
    features_clause = ' AND '.join([f"{fv.name} IS NOT NULL" for fv in feature_views])
    entties_select = ", ".join(f"MAX({fv.name}) as {fv.name}" for fv in feature_views)
    fv_select = ", ".join(f"MAX({fv.name}) as {fv.name}" for fv in feature_views)
    query = f"""
    SELECT 
        ds.account_id, 
        ds.status_id, 
        COALESCE(BOOL_OR(l.is_favourited), FALSE) AS is_favourited,
        COALESCE(BOOL_OR(l.is_replied), FALSE) AS is_replied,
        COALESCE(BOOL_OR(l.is_reblogged), FALSE) AS is_reblogged,
        COALESCE(BOOL_OR(l.is_reply_engaged_by_author), FALSE) AS is_reply_engaged_by_author,
        {fv_select}
    FROM {entity_table} as ds
    LEFT JOIN ({' UNION ALL '.join(queries)}) data ON {entities_and_clause}
    LEFT JOIN account_status_labels l
      ON l.account_id = ds.account_id AND l.status_id = ds.status_id
    GROUP BY ds.account_id, ds.status_id;
    """

    return query

def get_historical_features(entity_table: str, feature_views: list[FeatureView], db: Session):
    total = db.scalar(text(f"SELECT COUNT(*) FROM {entity_table}"))
    query = _get_historical_features_query(entity_table, feature_views)
    bar = tqdm(total=total, desc="Features", unit="samples")

    for row in db.exec(text(query)).mappings().yield_per(100):
        feats = {}
        for fv in feature_views:
            if row[fv.name] is None:
                feats |= {f"{fv.name}__{f.name}": None for f in fv.schema}
            else:
                feats |= {f"{fv.name}__{f.name}": value for f, value in zip(fv.schema, row[fv.name])}
        entities = {e: row[e] for e in ['account_id', 'status_id']}

        row = entities | {
            'label.is_favourited': row.is_favourited,
            'label.is_replied': row.is_replied,
            'label.is_reblogged': row.is_reblogged,
            'label.is_reply_engaged_by_author': row.is_reply_engaged_by_author,
        } | feats

        yield pd.Series(row)

        bar.update(1)

    bar.close()