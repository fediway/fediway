
from datetime import datetime
from pathlib import Path
import typer

from modules.fediway.datasets import DATASETS

app = typer.Typer(help="Dataset commands.")

def validate_dataset_name(name: str):
    if name not in DATASETS.keys():
        raise typer.BadParameter(
            f"Invalid dataset '{name}', must be any of: {', '.join(DATASETS.keys())}"
        )
    return name

@app.command("create")
def create_dataset(
    name: str = typer.Argument(
        ...,
        help="Name of dataset to create",
        callback=validate_dataset_name
    ),
    chunk_size: int = 100,
    test_size: float = 0.2,
    path: str = 'data/datasets',
) -> int:
    from app.core.db import get_db_session

    typer.echo(f"Creating dataset: {name}")

    dataset_cls = DATASETS[name]
    db = next(get_db_session())

    dataset_path = Path(path) / f"{name}_{datetime.now().strftime('%d_%m_%Y')}"
    dataset = dataset_cls.extract(db, chunk_size=chunk_size)
    dataset = dataset.train_test_split(test_size=test_size)
    dataset.save_to_disk(str(dataset_path))

    typer.echo(dataset)
    typer.echo(f"Saved dataset to path {dataset_path}")

    return 0