
import numpy as np
from datasets import load_from_disk
from pathlib import Path
import typer

from modules.fediway.rankers import Kirby

app = typer.Typer(help="Dataset commands.")

def validate_kirby_model(name: str):
    if name not in Kirby.MODELS:
        raise typer.BadParameter(
            f"Invalid ranker '{name}', must be any of: {', '.join(Kirby.MODELS)}"
        )
    return name

@app.command("kirby")
def train_kirby(
    dataset: str = typer.Argument(
        ...,
        help="Name of dataset used for training",
    ),
    model: str = typer.Option(
        'linear',
        help="Model name",
        callback=validate_kirby_model
    ),
    features: str = 'ranker',
    label: str = 'label.is_favourited',
    dataset_path: str = 'data/datasets',
    seed: int = 42
) -> int:
    from app.core.fs import get_feature_store
    np.random.seed(seed)

    fs = get_feature_store()

    dataset = load_from_disk(Path(dataset_path) / dataset)
    features = [f for f in dataset['train'].features.keys() if not f.startswith('label.')]

    ranker = getattr(Kirby, model)(features=features, label=label)
    ranker.train(dataset['train'])
    train_metrics = ranker.evaluate(dataset['train'])
    test_metrics = ranker.evaluate(dataset['test'])

    print("train", train_metrics)
    print("test", test_metrics)

    return 0