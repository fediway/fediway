import typer

app = typer.Typer(help="Feast commands.")


@app.command("apply")
def apply():
    from features import ENTITIES, FEATURE_VIEWS, FEATURES_SERVICES
    from shared.core.feast import feature_store

    feature_store.apply(ENTITIES)
    feature_store.apply(FEATURE_VIEWS)
    feature_store.apply(FEATURES_SERVICES)
