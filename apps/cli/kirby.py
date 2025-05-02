
from datetime import datetime, date
from config import config
import typer

app = typer.Typer(help="Kirby commands.")

@app.command("create-dataset")
def create_dataset(
    test_size: float = 0.2,
    path: str = config.fediway.datasets_path,
    start_date: datetime | None = None,
    end_date: datetime = datetime.now()
) -> int:
    from modules.fediway.rankers.kirby import KirbyDataset
    from shared.core.rw import rw_session, engine
    from shared.core.feast import feature_store

    from sklearn.model_selection import train_test_split

    typer.echo(f"Creating dataset...")

    if start_date:
        name = f"kirby_{start_date.strftime('%Y_%m_%d')}-{end_date.strftime('%Y_%m_%d')}"
    else:
        name = f"kirby_{end_date.strftime('%Y_%m_%d')}"
    
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

    if path.startswith('s3://'):
        import s3fs
        s3 = s3fs.S3FileSystem(endpoint_url=config.fediway.datasets_s3_endpoint)
        with s3.open(f"{path}/{name}/train.csv",'w') as f:
            train_df.to_csv(f)
        with s3.open(f"{path}/{name}/test.csv",'w') as f:
            test_df.to_csv(f)
    else:
        dataset_path = Path(path) / name
        dataset_path.mkdir(exist_ok=True, parents=True)
        train_df.to_csv(f"{path}/{name}/train.csv")
        test_df.to_csv(f"{path}/{name}/test.csv")

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
    label: str = 'label.is_favourited',
    path: str = config.fediway.datasets_path,
    seed: int = 42
) -> int:
    from modules.fediway.rankers.kirby import Kirby
    from shared.core.feast import feature_store
    import pandas as pd
    import numpy as np

    np.random.seed(seed)
    dataset_path = f"{path}/{dataset}"

    if dataset_path.startswith('s3://'):
        import s3fs
        s3 = s3fs.S3FileSystem(endpoint_url=config.fediway.datasets_s3_endpoint)
        with s3.open(f"{dataset_path}/train.csv",'r') as f:
            train = pd.read_csv(f)
        with s3.open(f"{dataset_path}/test.csv",'r') as f:
            test = pd.read_csv(f)
    else:
        train = pd.read_csv(f"{dataset_path}/train.csv")
        test = pd.read_csv(f"{dataset_path}/test.csv")

    features = [c for c in train.columns if '__' in c]
    labels = [c for c in train.columns if 'label.' in c]

    ranker = getattr(Kirby, model)(features=features, label=label)
    ranker.train(train)
    train_metrics = ranker.evaluate(train)
    test_metrics = ranker.evaluate(test)

    print("train", train_metrics)
    print("test", test_metrics)

    return 0