
import typer

app = typer.Typer()

@app.command()
def hello():
    typer.echo("Hello World!")

@app.command()
def make_controller(name: str):
    """Create a controller."""
    typer.echo(f"Controller {name} created!")