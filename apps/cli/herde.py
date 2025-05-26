import typer

from config import config

app = typer.Typer(help="Schwarm commands.")


def get_client():
    from arango import ArangoClient

    return ArangoClient(hosts=config.fediway.arango_hosts)


@app.command("migrate")
def migrate():
    client = get_client()

    sys_db = client.db(
        "_system",
        username=config.fediway.arango_user,
        password=config.fediway.arango_pass,
    )

    if not sys_db.has_database(config.fediway.arango_name):
        sys_db.create_database(config.fediway.arango_name)
        typer.echo(f"✅ Created {config.fediway.arango_name} arango database.")
    else:
        typer.echo(f"Arango database {config.fediway.arango_name} already exists.")

    db = client.db(
        config.fediway.arango_name,
        username=config.fediway.arango_user,
        password=config.fediway.arango_pass,
        verify=True,
    )

    if not db.has_graph(config.fediway.arango_graph):
        graph = db.create_graph(config.fediway.arango_graph)
        typer.echo(f"✅ Created graph '{config.fediway.arango_graph}'.")
    else:
        graph = db.graph(config.fediway.arango_graph)

    if not graph.has_vertex_collection("accounts"):
        accounts = graph.create_vertex_collection("accounts")
        typer.echo(f"✅ Created vertex 'accounts'.")

    if not graph.has_vertex_collection("statuses"):
        statuses = graph.create_vertex_collection("statuses")
        statuses.add_index(fields=['created_at'], type='skiplist')
        statuses.add_index(fields=['language'], type='hash')
        typer.echo(f"✅ Created vertex 'statuses'.")

    if not graph.has_vertex_collection("tags"):
        tags = graph.create_vertex_collection("tags")
        typer.echo(f"✅ Created vertex 'tags'.")

    if not graph.has_edge_definition("follows"):
        graph.create_edge_definition(
            edge_collection="follows",
            from_vertex_collections=["accounts"],
            to_vertex_collections=["accounts"],
        )
        typer.echo(f"✅ Created edge 'follows'.")

    if not graph.has_edge_definition("tagged"):
        graph.create_edge_definition(
            edge_collection="tagged",
            from_vertex_collections=["statuses"],
            to_vertex_collections=["tags"],
        )
        typer.echo(f"✅ Created edge 'tagged'.")

    if not graph.has_edge_definition("mentioned"):
        graph.create_edge_definition(
            edge_collection="mentioned",
            from_vertex_collections=["statuses"],
            to_vertex_collections=["accounts"],
        )
        typer.echo(f"✅ Created edge 'mentioned'.")

    if not graph.has_edge_definition("created"):
        graph.create_edge_definition(
            edge_collection="created",
            from_vertex_collections=["accounts"],
            to_vertex_collections=["statuses"],
        )
        typer.echo(f"✅ Created edge 'created'.")

    if not graph.has_edge_definition("engaged"):
        engaged = graph.create_edge_definition(
            edge_collection="engaged",
            from_vertex_collections=["accounts"],
            to_vertex_collections=["statuses"],
        )
        engaged.add_index(fields=['event_time'], type='skiplist')
        engaged.add_index(fields=['type'], type='hash')
        typer.echo(f"✅ Created edge 'engaged'.")


@app.command("seed")
def seed():
    from shared.core.db import db_session
    from shared.core.herde import graph
    from shared.services.seed_herde_service import SeedHerdeService

    with db_session() as db:
        SeedHerdeService(db, graph).seed()

    typer.echo("✅ Seeding completed!")


@app.command("similar-accounts")
def similar_accounts(account_id: int):
    from shared.core.herde import db

    similar_accounts_query = """
        LET targetAccount = DOCUMENT("accounts", @account_id)
        LET engagedStatuses = (
            FOR f IN favourited FILTER f._from == targetAccount._id RETURN f._to
        )
        LET totalEngagedStatuses = LENGTH(engagedStatuses)

        LET similarAccounts = (
            FOR statusId IN engagedStatuses
                FOR f IN favourited
                    FILTER f._to == statusId
                    FILTER f._from != targetAccount._id
                    COLLECT accountId = f._from WITH COUNT INTO overlap
                    LET jaccardSimilarity = overlap / (totalEngagedStatuses + LENGTH(
                        FOR fav IN favourited
                        FILTER fav._from == accountId
                        COLLECT WITH COUNT INTO total
                        RETURN total
                    )[0] - overlap)
                    FILTER overlap >= @min_overlap // Filter weak matches early
                    SORT jaccardSimilarity DESC, overlap DESC
                    LIMIT @limit
                    RETURN {
                        account: DOCUMENT("accounts", accountId),
                        overlap: overlap,
                        similarity: jaccardSimilarity,
                        favoriteStatuses: ( // Sample of common favorites
                            FOR fav IN favourited
                            FILTER fav._from == accountId
                            FILTER fav._to IN engagedStatuses
                            LIMIT 5
                            RETURN DOCUMENT(fav._to)
                        )
                    }
        )

        RETURN {
            target: targetAccount._key,
            totalFavorites: totalEngagedStatuses,
            similarAccounts: similarAccounts
        }
    """

    cursor = db.aql.execute(
        similar_accounts_query,
        bind_vars={"account_id": str(account_id), "min_overlap": 1, "limit": 50},
    )

    for result in cursor:
        print(result)


@app.command("compute-affinities")
def compute_affinities():
    import modules.utils as utils
    from modules.herde import Herde
    from shared.core.herde import db, graph

    herde = Herde(graph)

    with utils.duration("✅ Computed affinities in {:.3f} seconds."):
        query = """
        FOR follow IN follows
            LET a = follow._from
            LET b = follow._to

            // Count common favourites
            LET common = (
                FOR favA IN favourited
                    FILTER favA._from == a
                    FOR favB IN favourited
                        FILTER favB._from == b AND favB._to == favA._to
                        COLLECT WITH COUNT INTO cnt
                        RETURN cnt
            )[0]

            // Count favorites for a and b
            LET a_count = (
                FOR fav IN favourited
                    FILTER fav._from == a
                    COLLECT WITH COUNT INTO cnt
                    RETURN cnt
            )[0]
            LET b_count = (
                FOR fav IN favorites
                    FILTER fav._from == b
                    COLLECT WITH COUNT INTO cnt
                    RETURN cnt
            )[0]

            // Compute Jaccard
            LET union = a_count + b_count - (common ?? 0)
            FILTER union > 0
            LET jaccard = (common ?? 0) / union
            // Update affinities
            UPSERT { _from: a, _to: b }
            INSERT { _from: a, _to: b, jaccard: jaccard }
            UPDATE { jaccard: jaccard } IN affinities
        """
        db.aql.execute(query)
