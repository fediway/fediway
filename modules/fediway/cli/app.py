
import typer

from .dataset import app as dataset_app
from .train import app as train_app

app = typer.Typer()

app.add_typer(
    dataset_app,
    name="dataset",
    help="Manage datasets (create, preprocess, etc.)"
)

app.add_typer(
    train_app,
    name="train",
    help="Train a given model"
)