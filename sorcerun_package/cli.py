import click
import subprocess
import json
from .mongodb_utils import mongodb_server, init_mongodb
from contextlib import ExitStack


@click.group()
def sorcerun():
    pass


@sorcerun.group()
def mongo():
    pass


@mongo.command()
def init():
    db_path = click.prompt(
        "Please enter the path where you'd like to store the MongoDB database files"
    )
    db_name = click.prompt("Enter the name of the database to store runs")
    username = click.prompt("Please enter a new username for the MongoDB database")
    password = click.prompt(
        "Please enter a new password for the MongoDB database", hide_input=True
    )

    click.echo("\n")

    init_mongodb(
        db_path=db_path,
        db_name=db_name,
        username=username,
        password=password,
    )

    click.echo(
        "Initialization complete. Use `sorcerun mongo start` to start the configured mongodb server."
    )


@mongo.command()
def start():
    with open("auth.json", "r") as f:
        authjson = json.loads(f.read())
        conf_path = authjson["conf_path"]

    print(conf_path)
    with mongodb_server(conf_path):
        # TODO pipe log outputs to stdout or something nicely
        while True:
            pass


@sorcerun.command()
def omniboard():
    """
    Run Omniboard using the details saved in auth.json.
    """
    try:
        with open("auth.json", "r") as f:
            auth_data = json.load(f)

        mongodb_uri = f'mongodb://{auth_data["client_kwargs"]["username"]}:{auth_data["client_kwargs"]["password"]}@127.0.0.1:27017/{auth_data["db_name"]}?authSource=admin'

        click.echo("Starting Omniboard...")
        with ExitStack() as stack:
            omniboard_process = subprocess.Popen(["omniboard", "--mu", mongodb_uri])
            stack.callback(omniboard_process.terminate)
            omniboard_process.wait()

    except (FileNotFoundError, json.JSONDecodeError):
        click.echo("Error: auth.json file not found or is not a valid JSON file.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error occurred while running Omniboard: {e}")


if __name__ == "__main__":
    sorcerun()
