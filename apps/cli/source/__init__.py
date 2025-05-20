import typer

from .follows import app as follows_app

app = typer.Typer(help="Source commands.")

app.add_typer(
    follows_app,
    name="follows",
)
