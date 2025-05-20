import typer

app = typer.Typer(help="Follow sources.")


@app.command("triangular-loop")
def triangular_loop_command(account_id: int, limit: int = 10):
    from .triangular_loop import triangular_loop

    triangular_loop(account_id, limit)
