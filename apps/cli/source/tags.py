import typer

app = typer.Typer(help="Tag sources.")


@app.command("trending")
def trending(limit: int = 10, language: str = "en"):
    from apps.api.sources.tags import TrendingTagsSource
    from shared.core.redis import get_redis
    from shared.core.rw import rw_session

    with rw_session() as rw:
        source = TrendingTagsSource(r=get_redis(), rw=rw, language=language)

        source.reset()
        candidates = source.store()

        tag_ids = list(source.collect(limit))
        names = {c["tag_id"]: c["name"] for c in candidates}

        for tag_id in tag_ids:
            print(f"#{names.get(tag_id, tag_id)}")
