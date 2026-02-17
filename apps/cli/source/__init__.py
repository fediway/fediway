import typer

from .accounts import app as accounts_app
from .statuses import app as statuses_app
from .tags import app as tags_app

app = typer.Typer(help="Source commands.")

app.add_typer(
    statuses_app,
    name="statuses",
)

app.add_typer(
    tags_app,
    name="tags",
)

app.add_typer(
    accounts_app,
    name="accounts",
)
