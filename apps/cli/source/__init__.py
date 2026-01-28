import typer

from .statuses import app as statuses_app

app = typer.Typer(help="Source commands.")

app.add_typer(
    statuses_app,
    name="statuses",
)
