
import json
import typer

from config import config

app = typer.Typer(help="Debezium commands.")

@app.command("setup")
def setup():
    import requests

    url = config.db.debezium_url + '/connectors'

    response = requests.post(url, json=config.db.debezium_connector_config)

    if response.status_code == 201:
        typer.echo(f"✅ Successfully created connector '{config.db.debezium_connector_name}', ready to stream postgres data!")
    else:
        typer.echo(json.dumps(json.loads(response.text), indent=4))