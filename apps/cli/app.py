
import typer

from .dataset import app as dataset_app
from .feast import app as feast_app
from .train import app as train_app
from .herde import app as herde_app
from .risingwave import app as risingwave_app
from .kafka import app as kafka_app
from .qdrant import app as qdrant_app

app = typer.Typer()

app.add_typer(
    dataset_app,
    name="dataset",
    help="Manage datasets (create, preprocess, etc.)"
)

app.add_typer(
    feast_app,
    name="feast",
    help="Feast commands (feature store)"
)

app.add_typer(
    train_app,
    name="train",
    help="Train a given model"
)

app.add_typer(
    herde_app,
    name="herde",
    help="Run actions on the Herde (in-memory interaction graph)"
)

app.add_typer(
    kafka_app,
    name="kafka",
    help="Run actions for RisingWave (Streaming Platform)"
)

app.add_typer(
    qdrant_app,
    name="qdrant",
    help="Run actions for Qdrant (Vector Database)"
)

app.add_typer(
    risingwave_app,
    name="risingwave",
    help="Run actions on the RisingWave (Streaming Database)"
)