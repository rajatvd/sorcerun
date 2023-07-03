import click
import time
from sklearn.model_selection import ParameterGrid
import os
import subprocess
import json, yaml
from contextlib import ExitStack
from .mongodb_utils import mongodb_server, init_mongodb
from .sacred_utils import load_adapter_function, run_sacred_experiment
from .incense_utils import squish_dict, unsquish_dict
from .globals import AUTH_FILE


@click.group()
def sorcerun():
    pass


@sorcerun.command()
@click.argument("python_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--auth_path", default=AUTH_FILE, help="Path to sorcerun_auth.json file.")
def run(python_file, config_file, auth_path):
    # Load the adapter function from the provided Python file
    adapter_func = load_adapter_function(python_file)

    # Load the config from the provided YAML file
    with open(config_file, "r") as file:
        config = yaml.safe_load(file)

    # Run the Sacred experiment with the provided adapter function and config
    run_sacred_experiment(adapter_func, config, auth_path)


@sorcerun.command()
@click.argument("python_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("grid_config_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--auth_path", default=AUTH_FILE, help="Path to sorcerun_auth.json file.")
def grid_run(python_file, grid_config_file, auth_path):
    # Load the adapter function from the provided Python file
    adapter_func = load_adapter_function(python_file)

    # Load the config from the provided YAML file
    with open(grid_config_file, "r") as file:
        config = yaml.safe_load(file)

    config = squish_dict(config)
    for k, v in config.items():
        if type(v) != list:
            config[k] = [v]

    param_grid = ParameterGrid([config])
    total_num_params = len(param_grid)
    print(f"Parameter grid contains {total_num_params} combinations")

    # Run the Sacred experiment with the provided adapter function and config
    for i, param in enumerate(param_grid):
        conf = unsquish_dict(param)
        print(
            "-" * 5
            + "GRID RUN INFO: "
            + f"Starting run {i+1}/{total_num_params}"
            + "-" * 5
        )
        print(f"Config:\n{conf}")
        run_sacred_experiment(adapter_func, conf, auth_path)
        print(
            "-" * 5
            + "GRID RUN INFO: "
            + f"Completed run {i+1}/{total_num_params}"
            + "-" * 5
        )


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
    with open(AUTH_FILE, "r") as f:
        authjson = json.loads(f.read())
        conf_path = authjson["conf_path"]

    print(conf_path)
    with mongodb_server(conf_path):
        while True:
            time.sleep(10)


@sorcerun.command()
def omniboard():
    """
    Run Omniboard using the details saved in {AUTH_FILE}.
    """
    try:
        with open(AUTH_FILE, "r") as f:
            auth_data = json.load(f)

        atlas = auth_data.get("atlas_connection_string", 0)
        mongodb_uri = (
            f"{atlas}/{auth_data['db_name']}"
            if atlas != 0
            else f"mongodb://{auth_data['client_kwargs']['username']}:{auth_data['client_kwargs']['password']}@{auth_data['client_kwargs']['host']}:{auth_data['client_kwargs']['port']}/{auth_data['db_name']}?authSource=admin"
        )
        # mongodb_uri = f'mongodb://{auth_data["client_kwargs"]["username"]}:{auth_data["client_kwargs"]["password"]}@127.0.0.1:27017/{auth_data["db_name"]}?authSource=admin'

        click.echo("Starting Omniboard...")
        with ExitStack() as stack:
            omniboard_process = subprocess.Popen(["omniboard", "--mu", mongodb_uri])
            stack.callback(omniboard_process.terminate)
            omniboard_process.wait()

    except (FileNotFoundError, json.JSONDecodeError):
        click.echo(
            f"Error: {AUTH_FILE} file not found or is not a valid JSON file. Run `sorcerun mongo init` to initialize this json file."
        )
    except subprocess.CalledProcessError as e:
        click.echo(f"Error occurred while running Omniboard: {e}")


@sorcerun.command()
def screen():
    screen_session_name = "sorcerun"

    # result = subprocess.Popen("screen -ls", shell=True, stdout=subprocess.PIPE)
    # output = "\n".join(str(a) for a in result.stdout.readlines())

    # click.echo(output)
    # if screen_session_name in output:
    #     click.echo(f"Screen session '{screen_session_name}' already exists.")
    #     return

    # Check if in conda environment
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", None)
    activate_conda = f"conda activate {conda_env}\n" if conda_env else ""

    # Start new detached screen session
    screen_command = ["screen", "-dmS", screen_session_name]
    subprocess.Popen(screen_command)

    # # Start 'sorcerun mongo start' in first window
    # screen_command = [
    #     "screen",
    #     "-S",
    #     screen_session_name,
    #     "-X",
    #     "stuff",
    #     activate_conda + "sorcerun mongo start\n",
    # ]
    # subprocess.Popen(screen_command)

    # # Name the first window
    # screen_command = [
    #     "screen",
    #     "-S",
    #     screen_session_name,
    #     "-p",
    #     "0",
    #     "-X",
    #     "title",
    #     "mongo_start",
    # ]
    # subprocess.Popen(screen_command)

    # Create new window
    screen_command = [
        "screen",
        "-S",
        screen_session_name,
        "-X",
        "screen",
        "-t",
        "mongodb",
    ]
    subprocess.Popen(screen_command)

    # Start 'sorcerun mongo start' in first window
    screen_command = [
        "screen",
        "-S",
        screen_session_name,
        "-p",
        "mongodb",
        "-X",
        "stuff",
        activate_conda + "sorcerun mongo start\n",
    ]
    subprocess.Popen(screen_command)

    screen_command = [
        "screen",
        "-S",
        screen_session_name,
        "-p",
        "1",
        "-X",
        "rename",
        "mongodb",
    ]
    subprocess.Popen(screen_command)

    # Create new window
    screen_command = [
        "screen",
        "-S",
        screen_session_name,
        "-X",
        "screen",
        "-t",
        "omniboard",
    ]
    subprocess.Popen(screen_command)

    # Start 'sorcerun omniboard' in second window
    screen_command = [
        "screen",
        "-S",
        screen_session_name,
        "-p",
        "omniboard",
        "-X",
        "stuff",
        activate_conda + "sorcerun omniboard\n",
    ]
    subprocess.Popen(screen_command)

    screen_command = [
        "screen",
        "-S",
        screen_session_name,
        "-p",
        "2",
        "-X",
        "title",
        "omniboard",
    ]
    subprocess.Popen(screen_command)

    screen_command = [
        "screen",
        "-S",
        screen_session_name,
        "-p",
        "0",
        "-X",
        "kill",
    ]
    subprocess.Popen(screen_command)


if __name__ == "__main__":
    sorcerun()