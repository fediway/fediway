
from datetime import datetime, date
from pathlib import Path
from config import config
import typer

app = typer.Typer(help="Kirby commands.")

@app.command("create-dataset")
def create_dataset(
    test_size: float = 0.2,
    path: str = 'data/datasets',
    start_date: datetime | None = None,
    end_date: datetime = datetime.now()
) -> int:
    from modules.fediway.rankers.kirby import KirbyDataset
    from shared.core.rw import rw_session, engine
    from shared.core.feast import feature_store

    from sklearn.model_selection import train_test_split
    from pathlib import Path

    typer.echo(f"Creating dataset...")

    if start_date:
        name = f"kirby_{start_date.strftime('%d_%m_%Y')}-{end_date.strftime('%d_%m_%Y')}"
    else:
        name = f"kirby_{end_date.strftime('%d_%m_%Y')}"
    
    with rw_session() as db:
        df = KirbyDataset.extract(feature_store, db, name, start_date, end_date)

    unique_account_ids = df['account_id'].unique()
    train_accounts, test_accounts = train_test_split(
        unique_account_ids, 
        test_size=test_size, 
        random_state=42
    )
    train_df = df[df['account_id'].isin(train_accounts)]
    test_df = df[df['account_id'].isin(test_accounts)]
    dataset_path = Path(path) / name
    dataset_path.mkdir(exist_ok=True, parents=True)

    train_df.to_csv(dataset_path / 'train.csv')
    test_df.to_csv(dataset_path / 'test.csv')

    typer.echo(f"Saved dataset to path {dataset_path}")

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
    features: str = 'ranker',
    label: str = 'label.is_favourited',
    dataset_path: str = 'data/datasets',
    seed: int = 42
) -> int:
    from modules.fediway.rankers.kirby import Kirby
    from shared.core.feast import feature_store
    import pandas as pd
    import numpy as np

    np.random.seed(seed)
    dataset_path = Path(dataset_path) / dataset

    train = pd.read_csv(dataset_path / 'train.csv')
    test = pd.read_csv(dataset_path / 'test.csv')

    features = [c for c in train.columns if '__' in c]

    ranker = getattr(Kirby, model)(features=features, label=label)
    ranker.train(train)
    train_metrics = ranker.evaluate(train)
    test_metrics = ranker.evaluate(test)

    print("train", train_metrics)
    print("test", test_metrics)

    return 0