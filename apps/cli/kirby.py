
from pathlib import Path
import typer

app = typer.Typer(help="Kirby commands.")

@app.command("create-dataset")
def create_dataset(
    test_size: float = 0.2,
    path: str = 'data/datasets',
) -> int:
    from shared.core.rw import get_rw_session, engine
    from shared.core.feast import get_feature_store

    typer.echo(f"Creating dataset: {name}")

    dataset_cls = DATASETS[name]

    name = f"{name}_{datetime.now().strftime('%d_%m_%Y')}"
    
    rw = next(get_rw_session())
    fs = get_feature_store()
    dataset = dataset_cls.extract(fs, rw, name)

    dataset_path = Path(path) / name
    dataset = dataset.train_test_split(test_size=test_size)
    dataset.save_to_disk(str(dataset_path))

    typer.echo(dataset)
    typer.echo(f"Saved dataset to path {dataset_path}")

    rw.close()

    return 0

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
    from shared.core.feast import get_feature_store
    import numpy as np
    from datasets import load_from_disk

    np.random.seed(seed)

    fs = get_feature_store()

    # fv = fs.get_feature_view("account_engagement_all")

    dataset = load_from_disk(Path(dataset_path) / dataset)
    features = [f for f in dataset['train'].features.keys() if "__" in f]

    ranker = getattr(Kirby, model)(features=features, label=label)
    ranker.train(dataset['train'])
    train_metrics = ranker.evaluate(dataset['train'])
    test_metrics = ranker.evaluate(dataset['test'])

    print("train", train_metrics)
    print("test", test_metrics)

    return 0