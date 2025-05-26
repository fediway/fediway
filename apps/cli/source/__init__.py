import typer

from .follows import app as follows_app
from .statuses import app as statuses_app

app = typer.Typer(help="Source commands.")

app.add_typer(
    follows_app,
    name="follows",
)

app.add_typer(
    statuses_app,
    name="statuses",
)
