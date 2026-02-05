import typer

from .feast import app as feast_app
from .kafka import app as kafka_app
from .orbit import app as orbit_app
from .qdrant import app as qdrant_app
from .risingwave import app as risingwave_app
from .source import app as source_app

app = typer.Typer()

app.add_typer(source_app, name="source")

app.add_typer(feast_app, name="feast", help="Feast commands (feature store)")

app.add_typer(orbit_app, name="orbit", help="Orbit commands (community embeddings)")

app.add_typer(kafka_app, name="kafka", help="Run actions for RisingWave (Streaming Platform)")

app.add_typer(qdrant_app, name="qdrant", help="Run actions for Qdrant (Vector Database)")

app.add_typer(
    risingwave_app,
    name="risingwave",
    help="Run actions on the RisingWave (Streaming Database)",
)
