
import typer

from .dataset import app as dataset_app
from .debezium import app as debezium_app
from .train import app as train_app
from .herde import app as herde_app
from .risingwave import app as risingwave_app

app = typer.Typer()

app.add_typer(
    dataset_app,
    name="dataset",
    help="Manage datasets (create, preprocess, etc.)"
)

app.add_typer(
    debezium_app,
    name="debezium",
    help="Usefull commands for debezium (postgres stream)"
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
    risingwave_app,
    name="risingwave",
    help="Run actions on the RisingWave (Streaming Database)"
)