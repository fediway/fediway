
from modules.fediway.rankers.kirby.features import LABELS
from datetime import datetime, date
from loguru import logger
import typer

from config import config

app = typer.Typer(help="Kirby commands.")

@app.command("create-dataset")
def create_dataset(
    test_size: float = 0.2,
    path: str = config.fediway.datasets_path,
    start_date: datetime | None = None,
    end_date: datetime = datetime.now()
) -> int:
    from modules.fediway.rankers.kirby.dataset import create_dataset
    from shared.core.rw import rw_session, engine
    from shared.core.feast import feature_store

    from pathlib import Path
    from sklearn.model_selection import train_test_split

    typer.echo(f"Creating dataset...")

    if start_date:
        name = f"kirby_{start_date.strftime('%Y_%m_%d')}-{end_date.strftime('%Y_%m_%d')}"
    else:
        name = f"kirby_{end_date.strftime('%Y_%m_%d')}"
    dataset_path = f"{path}/{name}"

    storage_options = {'client_kwargs': {'endpoint_url': config.fediway.datasets_s3_endpoint}}
    
    with rw_session() as db:
        create_dataset(
            dataset_path,
            feature_store,
            db, 
            name, 
            start_date, 
            end_date, 
            test_size, 
            storage_options=storage_options
        )
    
    typer.echo(f"Saved dataset to path {path}/{name}")

    return 0

def validate_kirby_model(name: str):
    from modules.fediway.rankers.kirby import Kirby
    if name not in Kirby.MODELS:
        raise typer.BadParameter(
            f"Invalid ranker '{name}', must be any of: {', '.join(Kirby.MODELS)}"
        )
    return name

@app.command("train")
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
    labels: list[str] = LABELS,
    path: str = config.fediway.datasets_path,
    seed: int = 42
) -> int:
    from modules.fediway.rankers.kirby import Kirby
    from shared.core.feast import feature_store
    from dask import dataframe as dd
    import pandas as pd
    import numpy as np

    np.random.seed(seed)
    dataset_path = f"{path}/{dataset}"

    storage_options = {'client_kwargs': {'endpoint_url': config.fediway.datasets_s3_endpoint}}
    train = dd.read_parquet(
        f"{dataset_path}/train/",
        storage_options=storage_options,
    ).compute()
    test = dd.read_parquet(
        f"{dataset_path}/test/",
        storage_options=storage_options,
    ).compute()

    features = [c for c in train.columns if '__' in c]

    logger.info(f"[Train] size: {len(train)}")
    for label in labels:
        logger.info(f"[Train] {label} count: {train[label].values.sum()}")
    logger.info(f"[Test] size: {len(test)}")
    for label in labels:
        logger.info(f"[Test] {label} count: {test[label].values.sum()}")

    ranker = getattr(Kirby, model)(features=features, labels=labels)
    ranker.train(train)
    train_metrics = ranker.evaluate(train)
    test_metrics = ranker.evaluate(test)

    print("train", train_metrics)
    print("test", test_metrics)

    return 0