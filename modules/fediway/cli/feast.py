
import typer

from config import config

app = typer.Typer(help="Feast commands.")

@app.command("apply")
def apply():
    from app.core.feast import feature_store
    from app.features import ENTITIES, FEATURE_VIEWS, FEATURES_SERVICES

    feature_store.apply(ENTITIES)
    feature_store.apply(FEATURE_VIEWS)
    feature_store.apply(FEATURES_SERVICES)