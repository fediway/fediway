from datetime import datetime

import typer
from loguru import logger

from config import config

app = typer.Typer(help="Kirby commands.")


@app.command("create-dataset")
def create_dataset(
    test_size: float = 0.2,
    path: str = config.fediway.datasets_path,
    start_date: datetime | None = None,
    end_date: datetime = datetime.now(),
) -> int:
    from modules.fediway.rankers.kirby.dataset import create_dataset
    from shared.core.feast import feature_store
    from shared.core.rw import rw_session

    typer.echo(f"Creating dataset...")

    if start_date:
        name = (
            f"kirby_{start_date.strftime('%Y_%m_%d')}-{end_date.strftime('%Y_%m_%d')}"
        )
    else:
        name = f"kirby_{end_date.strftime('%Y_%m_%d')}"
    dataset_path = f"{path}/{name}"

    storage_options = {
        "client_kwargs": {"endpoint_url": config.fediway.datasets_s3_endpoint}
    }

    with rw_session() as db:
        create_dataset(
            dataset_path,
            feature_store,
            db,
            name,
            start_date,
            end_date,
            test_size,
            storage_options=storage_options,
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
        "linear", help="Model name", callback=validate_kirby_model
    ),
    labels: list[str] | None = None,
    path: str = config.fediway.datasets_path,
    save_path: str | None = None,
    seed: int = 42,
) -> int:
    import numpy as np
    from pathlib import Path
    from dask import dataframe as dd

    from modules.fediway.rankers.kirby.features import LABELS
    from modules.fediway.rankers.kirby import Kirby, get_feature_views
    from shared.core.feast import feature_store

    if labels is None:
        labels = LABELS

    np.random.seed(seed)
    dataset_path = f"{path}/{dataset}"

    storage_options = {
        "client_kwargs": {"endpoint_url": config.fediway.datasets_s3_endpoint}
    }
    train = dd.read_parquet(
        f"{dataset_path}/train/",
        storage_options=storage_options,
    ).compute()
    test = dd.read_parquet(
        f"{dataset_path}/test/",
        storage_options=storage_options,
    ).compute()

    features = []

    for fv in get_feature_views(feature_store):
        for field in fv.schema:
            if field in fv.entities:
                continue
            features.append(f"{fv.name}__{field.name}")

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

    if save_path is not None:
        save_path = Path(save_path)
        save_path.mkdir(exist_ok=True, parents=True)
        ranker.save(save_path)

    return 0


@app.command("test")
def test_kirby(
    model_path: str = typer.Argument(
        ...,
        help="Path to the pretrained model",
    ),
    dataset: str = typer.Argument(
        ...,
        help="Name of dataset used for training",
    ),
    labels: list[str] | None = None,
    path: str = config.fediway.datasets_path,
    seed: int = 42,
) -> int:
    import numpy as np
    from pathlib import Path
    from dask import dataframe as dd

    from modules.fediway.rankers.kirby.features import LABELS
    from modules.fediway.rankers.kirby import Kirby, get_feature_views
    from shared.core.feast import feature_store

    if labels is None:
        labels = LABELS

    np.random.seed(seed)

    ranker = Kirby.load(model_path)

    dataset_path = f"{path}/{dataset}"

    storage_options = {
        "client_kwargs": {"endpoint_url": config.fediway.datasets_s3_endpoint}
    }
    test = dd.read_parquet(
        f"{dataset_path}/test/",
        storage_options=storage_options,
    ).compute()

    logger.info(f"[Test] size: {len(test)}")
    for label in labels:
        logger.info(f"[Test] {label} count: {test[label].values.sum()}")

    print("test", ranker.evaluate(test))

    return 0
