import click
import subprocess
import json, yaml
from contextlib import ExitStack
from .mongodb_utils import mongodb_server, init_mongodb
from .sacred_utils import load_adapter_function, run_sacred_experiment


@click.group()
def sorcerun():
    pass


@sorcerun.command()
@click.argument("python_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
def run(python_file, config_file):
    # Load the adapter function from the provided Python file
    adapter_func = load_adapter_function(python_file)

    # Load the config from the provided YAML file
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)

    # Run the Sacred experiment with the provided adapter function and config
    run_sacred_experiment(adapter_func, config)


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
