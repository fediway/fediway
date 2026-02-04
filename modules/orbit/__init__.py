from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlmodel import Session, select

from shared.utils.logging import Timer, log_debug


def load_tag_engagements_from_file(path):
    import ast

    df = pd.read_csv(path)
    df["accounts"] = df["accounts"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) and x != "None" and x != "nan" else []
    )
    df["accounts"] = df["accounts"].apply(lambda x: [] if len(x) == 1 and x[0] is None else x)

    return df


def load_tagsimilarities_from_db(db: Session, start: datetime, end: datetime):
    text("""
        WITH base_engagements AS (
            SELECT
                e.account_id,
                e.author_id,
                e.status_id,
                st.tag_id
            FROM enriched_status_engagement_events e
            JOIN statuses_tags st ON st.status_id = e.status_id
            WHERE e.event_time > :start AND e.event_time <= :end
            AND e.author_silenced_at IS NULL
            AND e.account_silenced_at IS NULL
            AND e.sensitive != true
        ),
        orbit_tag_performance AS (
            SELECT
                tag_id,
                COUNT(DISTINCT account_id) AS num_engaged_accounts,
                COUNT(DISTINCT author_id) AS num_authors,
                COUNT(DISTINCT status_id) AS num_statuses
            FROM base_engagements
            GROUP BY tag_id
        ),
        orbit_account_tag_engagements AS (
            SELECT DISTINCT account_id, tag_id
            FROM base_engagements
        ),
        qualified_tags AS (
            SELECT tag_id
            FROM orbit_tag_performance
            WHERE num_engaged_accounts >= 15
        )
        SELECT
            e1.tag_id AS tag1,
            e2.tag_id AS tag2,
            COUNT(DISTINCT e1.account_id)::FLOAT /
                SQRT(
                    MAX(t1.num_engaged_accounts) *
                    MAX(t2.num_engaged_accounts)
                ) AS cosine_sim
        FROM orbit_account_tag_engagements e1
        JOIN orbit_account_tag_engagements e2
            ON e2.account_id = e1.account_id
            AND e1.tag_id < e2.tag_id
        JOIN qualified_tags qt1 ON qt1.tag_id = e1.tag_id
        JOIN qualified_tags qt2 ON qt2.tag_id = e2.tag_id
        JOIN orbit_tag_performance t1 ON t1.tag_id = e1.tag_id
        JOIN orbit_tag_performance t2 ON t2.tag_id = e2.tag_id
        GROUP BY e1.tag_id, e2.tag_id;
    """)

    # todo:


def load_tag_engagements_from_db(db: Session, start: datetime, end: datetime):
    query = text("""
        WITH engagements AS (
            SELECT
                f.account_id,
                f.status_id,
                0 AS type,
                f.id as entity_id,
                f.created_at AS event_time
            FROM favourites f

            UNION

            SELECT
                s.account_id,
                s.reblog_of_id AS status_id,
                1 AS type,
                s.id as entity_id,
                s.created_at AS event_time
            FROM statuses s
            WHERE s.reblog_of_id IS NOT NULL

            UNION

            SELECT
                s.account_id,
                s.in_reply_to_id AS status_id,
                2 AS type,
                s.id as entity_id,
                s.created_at AS event_time
            FROM statuses s
            WHERE s.in_reply_to_id IS NOT NULL

            UNION

            SELECT
                v.account_id,
                p.status_id as status_id,
                3 AS type,
                v.id as entity_id,
                v.created_at AS event_time
            FROM poll_votes v
            JOIN polls p ON p.id = v.poll_id

            UNION

            SELECT
                account_id,
                status_id,
                4 AS type,
                id as entity_id,
                created_at AS event_time
            FROM bookmarks

            UNION

            SELECT
                account_id,
                quoted_status_id as status_id,
                5 AS type,
                status_id as entity_id,
                created_at AS event_time
            FROM quotes
            WHERE state = 1
        )
        SELECT
            st.tag_id,
            array_agg(e.account_id) as accounts
        FROM
            engagements e
        JOIN
            statuses_tags st ON st.status_id = e.status_id
        WHERE e.event_time > :start AND e.event_time <= :end
        GROUP BY st.tag_id;
    """).params(start=start, end=end)

    with Timer() as t:
        result = db.execute(query)
        rows = result.all()

    log_debug("Loaded engagements", module="orbit", duration_ms=round(t.elapsed_ms, 2))

    if len(rows) == 0:
        return None

    return pd.DataFrame(rows)


def load_tag_similarities(db: Session, min_tag_similarity: float):
    query = text("""
    SELECT *
    FROM orbit_tag_similarities
    WHERE cosine_sim > :min_tag_similarity;
    """).params(min_tag_similarity=min_tag_similarity)

    with Timer() as t:
        result = db.execute(query)
        rows = result.all()

    log_debug("Loaded tag similarities", module="orbit", duration_ms=round(t.elapsed_ms, 2))

    if len(rows) == 0:
        return None

    return pd.DataFrame(rows)


def detect_communities(tag_similarities: pd.DataFrame):
    import networkx as nx
    from tqdm import tqdm

    G = nx.Graph()

    for tag_pair in tag_similarities.iloc:
        G.add_edge(int(tag_pair.tag1), int(tag_pair.tag2), weight=tag_pair.cosine_sim)

    print("Number of nodes:", G.number_of_nodes())
    print("Number of edges:", G.number_of_edges())

    communities = nx.community.louvain_communities(G)

    print("Number of communities:", len(communities))

    return communities
