
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
    from app.core.rw import get_rw_session
    from app.core.feast import get_feature_store

    typer.echo(f"Creating dataset: {name}")

    dataset_cls = DATASETS[name]
    
    rw = next(get_rw_session())
    fs = get_feature_store()
    dataset = dataset_cls.extract(fs, rw)

    dataset_path = Path(path) / f"{name}_{datetime.now().strftime('%d_%m_%Y')}"
    dataset = dataset.train_test_split(test_size=test_size)
    dataset.save_to_disk(str(dataset_path))

    typer.echo(dataset)
    typer.echo(f"Saved dataset to path {dataset_path}")

    rw.close()

    return 0