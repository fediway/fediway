from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy import text
import dask.dataframe as dd
import modules.utils as utils
import pandas as pd
import math


def load_tag_engagements_from_file(path):
    import ast

    df = pd.read_csv(path)
    df["accounts"] = df["accounts"].apply(
        lambda x: ast.literal_eval(x)
        if isinstance(x, str) and x != "None" and x != "nan"
        else []
    )
    df["accounts"] = df["accounts"].apply(
        lambda x: [] if len(x) == 1 and x[0] is None else x
    )

    return df


def load_tag_engagements_from_db(db: Session, start: datetime, end: datetime):
    query = text(f"""
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

    with utils.duration("Loaded engagements in {:.3f} seconds."):
        result = db.execute(query)
        rows = result.all()

    if len(rows) == 0:
        return None

    return pd.DataFrame(rows)


def detect_communities(
    tag_to_accounts: dict[int, set[int]], min_tag_similarity: float = 0.25
):
    from tqdm import tqdm
    import networkx as nx

    G = nx.Graph()
    bar = tqdm(total=len(tag_to_accounts) ** 2)

    for tag1 in tag_to_accounts.keys():
        for tag2 in tag_to_accounts.keys():
            bar.update(1)

            if tag1 <= tag2:
                continue

            # Get the sets of accounts for each tag
            accounts1 = tag_to_accounts[tag1]
            accounts2 = tag_to_accounts[tag2]

            # Calculate the components of the cosine similarity formula
            # |U_A ∩ U_B|
            intersection_size = len(accounts1.intersection(accounts2))

            # If there's no overlap, similarity is 0, we can skip the rest
            if intersection_size == 0:
                continue

            # Calculate the denominator: sqrt(|U_A|) * sqrt(|U_B|)
            denominator = math.sqrt(len(accounts1)) * math.sqrt(len(accounts2))

            # Avoid division by zero, though this shouldn't happen if a tag is in our map
            if denominator == 0:
                continue
            else:
                # Calculate the final similarity score
                similarity = intersection_size / denominator

            if similarity < min_tag_similarity:
                continue

            G.add_edge(tag1, tag2, weight=similarity)

    bar.close()

    print("Number of nodes:", G.number_of_nodes())
    print("Number of edges:", G.number_of_edges())

    communities = nx.community.louvain_communities(G)

    print("Number of communities:", len(communities))

    return communities
