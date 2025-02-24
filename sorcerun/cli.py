import click
import time
from sklearn.model_selection import ParameterGrid
import os
import subprocess
import json, yaml
from contextlib import ExitStack
from .mongodb_utils import mongodb_server, init_mongodb
from .sacred_utils import load_python_module, run_sacred_experiment
from .incense_utils import (
    squish_dict,
    unsquish_dict,
    process_and_save_grid_to_netcdf,
    process_and_save_grid_to_csv,
)
from .globals import (
    AUTH_FILE,
    TEMP_CONFIGS_DIR,
    FILE_STORAGE_ROOT,
    GRID_OUTPUTS,
    TEMPLATE_FILES,
)
from .slurm_utils import Job, poll_jobs

from prettytable import PrettyTable
import sys, ipdb, traceback


def info(type, value, tb):
    traceback.print_exception(type, value, tb)
    ipdb.pm()


@click.group()
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="debug",
)
def sorcerun(debug):
    if debug:
        sys.excepthook = info


@sorcerun.command()
def template():
    this_file_path = os.path.abspath(__file__)
    this_dir = os.path.dirname(this_file_path)

    os.makedirs(f"main", exist_ok=True)

    for file in TEMPLATE_FILES:
        # check if file already exists in current directory
        if os.path.exists(file):
            click.echo(f"File {file} already exists. Skipping creation.")
            continue

        path_to_template_file = os.path.join(this_dir, file)
        with open(path_to_template_file, "r") as f:
            click.echo(f"Creating file: {file}")
            with open(file, "w") as new_f:
                new_f.write(f.read())


@sorcerun.command()
@click.argument("python_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("config_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--file_root",
    "-f",
    default=FILE_STORAGE_ROOT,
    type=click.Path(file_okay=False),
    help="Root directory for file storage",
)
@click.option("--auth_path", default=AUTH_FILE, help="Path to sorcerun_auth.json file.")
@click.option(
    "--mongo",
    "-m",
    is_flag=True,
    help="Use MongoObserver",
)
@click.option(
    "--dont_profile",
    is_flag=True,
    help="Don't use cProfile to profile the adapter function",
    default=False,
)
def run(
    python_file,
    config_file,
    file_root,
    auth_path,
    mongo,
    dont_profile,
):
    sorcerun_run(
        python_file,
        config_file,
        file_root=file_root,
        auth_path=auth_path,
        mongo=mongo,
        dont_profile=dont_profile,
    )


def sorcerun_run(
    python_file,
    config_file,
    file_root=FILE_STORAGE_ROOT,
    auth_path=AUTH_FILE,
    mongo=False,
    dont_profile=False,
):
    # Load the adapter function from the provided Python file
    adapter_module = load_python_module(python_file, force_reload=True)
    if not hasattr(adapter_module, "adapter"):
        raise KeyError(
            f"Adapter file at {python_file} does not have an attribute named adapter"
        )
    adapter_func = adapter_module.adapter

    _, config_ext = os.path.splitext(config_file)

    # Check extension of config file and load it accordingly
    if config_ext == ".json":
        with open(config_file, "r") as file:
            config = json.load(file)
    elif config_ext == ".yaml":
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
    elif config_ext == ".py":
        config_module = load_python_module(config_file, force_reload=True)
        if not hasattr(config_module, "config"):
            raise KeyError(
                f"Config file at {config_file} does not have an attribute named config"
            )
        config = config_module.config
    else:
        raise ValueError(
            f"Config file at {config_file} is not a valid JSON, YAML or python file"
        )

    # Run the Sacred experiment with the provided adapter function and config
    r = run_sacred_experiment(
        adapter_func,
        config,
        auth_path,
        use_mongo=mongo,
        file_storage_root=file_root,
        profile=not dont_profile,
    )
    return r


@sorcerun.command()
@click.argument(
    "python_file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.argument(
    "grid_config_file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--file_root",
    "-f",
    default=FILE_STORAGE_ROOT,
    type=click.Path(file_okay=False),
    help="Root directory for file storage",
)
@click.option(
    "--auth_path",
    default=AUTH_FILE,
    help="Path to sorcerun_auth.json file.",
)
@click.option(
    "--post_process",
    "-p",
    is_flag=True,
    help="Post process and save grid to netcdf",
)
@click.option(
    "--mongo",
    "-m",
    is_flag=True,
    help="Use MongoObserver",
)
def grid_run(
    python_file,
    grid_config_file,
    file_root,
    auth_path,
    post_process=False,
    mongo=False,
):
    sorcerun_grid_run(
        python_file,
        grid_config_file,
        file_root,
        auth_path,
        post_process=post_process,
        mongo=mongo,
    )


def sorcerun_grid_run(
    python_file,
    grid_config_file,
    file_root=FILE_STORAGE_ROOT,
    auth_path=AUTH_FILE,
    post_process=False,
    mongo=False,
):
    # Load the adapter function from the provided Python file
    adapter_module = load_python_module(python_file)
    if not hasattr(adapter_module, "adapter"):
        raise KeyError(
            f"Adapter file at {python_file} does not have an attribute named adapter"
        )
    adapter_func = adapter_module.adapter
    pre_grid_hook = getattr(adapter_module, "pre_grid_hook", None)
    post_grid_hook = getattr(adapter_module, "post_grid_hook", None)

    # Check extension of grid config file and load it accordingly
    _, config_ext = os.path.splitext(grid_config_file)

    if config_ext == ".yaml":
        with open(grid_config_file, "r") as file:
            config = yaml.safe_load(file)
        config = squish_dict(config)
        for k, v in config.items():
            if type(v) != list:
                config[k] = [v]
        param_grid = ParameterGrid([config])
        configs = [unsquish_dict(param) for param in param_grid]

    elif config_ext == ".py":
        config_module = load_python_module(grid_config_file)
        if not hasattr(config_module, "configs"):
            raise KeyError(
                f"Config file at {grid_config_file} does not have an attribute named configs"
            )
        configs = config_module.configs
    else:
        raise ValueError(
            f"Config file at {grid_config_file} is not a valid YAML or python file"
        )

    total_num_params = len(configs)
    print(f"Config grid contains {total_num_params} combinations")

    # Run the Sacred experiment with the provided adapter function and config
    for i, conf in enumerate(configs):
        print(
            "-" * 5
            + "GRID RUN INFO: "
            + f"Starting run {i+1}/{total_num_params}"
            + "-" * 5
        )
        if pre_grid_hook is not None:
            print(f"Running pre_grid_hook")
            pre_grid_hook(conf)

        print("Running experiment with config:")
        print(json.dumps(conf, indent=2))

        run_sacred_experiment(
            adapter_func,
            conf,
            auth_path,
            use_mongo=mongo,
            file_storage_root=file_root,
        )

        if post_grid_hook is not None:
            print(f"Running post_grid_hook")
            post_grid_hook(conf)

        print(
            "-" * 5
            + "GRID RUN INFO: "
            + f"Completed run {i+1}/{total_num_params}"
            + "-" * 5
        )

    if post_process:
        # Post process grid and save xarray to netcdf
        # check if each config in configs has the same "grid_id" and assign it to gid
        gid = configs[0].get("grid_id", None)
        same_gid = False
        if gid is not None:
            same_gid = all(conf.get("grid_id", None) == gid for conf in configs)

        if same_gid:
            print(f"All configs have the same grid_id: {gid}")
            print(f"Processing and saving grid to csv")
            process_and_save_grid_to_csv(gid, file_root=file_root)
        else:
            print(
                f"Configs do not have the same grid_id."
                + " Skipping processing and saving grid to csv"
            )


# %%
@sorcerun.command()
@click.argument(
    "python_file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.argument(
    "grid_config_file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.argument(
    "slurm_config_file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--file_root",
    "-f",
    default=FILE_STORAGE_ROOT,
    type=click.Path(file_okay=False),
    help="Root directory for file storage",
)
@click.option(
    "--auth_path",
    default=AUTH_FILE,
    help="Path to sorcerun_auth.json file.",
)
@click.option(
    "--post_process",
    "-p",
    is_flag=True,
    help="Post process and save grid to netcdf",
)
@click.option(
    "--mongo",
    "-m",
    is_flag=True,
    help="Use MongoObserver",
)
def grid_slurm(
    python_file,
    grid_config_file,
    slurm_config_file,
    file_root,
    auth_path,
    post_process=False,
    mongo=False,
):
    # Load the adapter function from the provided Python file
    adapter_module = load_python_module(python_file)
    if not hasattr(adapter_module, "adapter"):
        raise KeyError(
            f"Adapter file at {python_file} does not have an attribute named adapter"
        )

    # Check extension of grid config file and load it accordingly
    _, config_ext = os.path.splitext(grid_config_file)

    if config_ext == ".yaml":
        with open(grid_config_file, "r") as file:
            config = yaml.safe_load(file)
        config = squish_dict(config)
        for k, v in config.items():
            if type(v) != list:
                config[k] = [v]
        param_grid = ParameterGrid([config])
        configs = [unsquish_dict(param) for param in param_grid]

    elif config_ext == ".py":
        config_module = load_python_module(grid_config_file)
        if not hasattr(config_module, "configs"):
            raise KeyError(
                f"Config file at {grid_config_file} does not have an attribute named configs"
            )
        configs = config_module.configs
    else:
        raise ValueError(
            f"Config file at {grid_config_file} is not a valid YAML or python file"
        )

    total_num_params = len(configs)
    print(f"Config grid contains {total_num_params} combinations")

    # Load Slurm object from slurm_config_file
    slurm_module = load_python_module(slurm_config_file)
    if not hasattr(slurm_module, "slurm"):
        raise KeyError(
            f"slurm config file at {slurm_config_file} does not have an attribute named slurm"
        )
    slurm = slurm_module.slurm
    # slurm.add_arguments(wait=True)

    gid = configs[0].get("grid_id", None)
    same_gid = False
    if gid is not None:
        same_gid = all(conf.get("grid_id", None) == gid for conf in configs)

    gid_dir = None
    job_ids_file = None
    if same_gid:
        print(f"All configs have the same grid_id: {gid}")
        gid_dir = f"{file_root}/{GRID_OUTPUTS}/{gid}"
        os.makedirs(gid_dir, exist_ok=True)
        job_ids_file = os.path.join(gid_dir, "slurm_job_ids.txt")

    # make a temp dir to store the config files
    temp_configs_dir = os.path.join(gid_dir or file_root, TEMP_CONFIGS_DIR)
    os.makedirs(temp_configs_dir, exist_ok=True)

    jobs = []
    # Run the Sacred experiment with the provided adapter function and config
    for i, conf in enumerate(configs):
        print(
            "-" * 5
            + "GRID RUN INFO: "
            + f"Submitting run {i+1}/{total_num_params}"
            + "-" * 5
        )

        temp_config_file = os.path.join(temp_configs_dir, f"config_{i}.json")

        print(f"Saving the following config to {temp_config_file}")
        print(json.dumps(conf, indent=2))

        # Save config to a temp file
        with open(temp_config_file, "w") as file:
            json.dump(conf, file)

        slurm_command = (
            f"sorcerun run {python_file} {temp_config_file} --file_root {file_root} --auth_path {auth_path}"
            + ("-m" if mongo else "")
        )

        slurm.add_cmd(slurm_command)
        print(f"sbatch content:")
        print(slurm)

        cmd = "\n".join(
            (
                "sbatch" + " << EOF",
                slurm.script(shell="/bin/sh", convert=True),
                "EOF",
            )
        )
        slurm.run_cmds = slurm.run_cmds[:-1]

        # proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        # run the command and get the output
        out = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

        # extract slurm job id from out
        job_id = int(out.split()[-1])
        jobs.append(Job(job_id))

        # append the job id to the slurm_jobs.txt file if same_gid
        if same_gid:
            with open(job_ids_file, "a") as file:
                file.write(f"{job_id}\n")

        print(
            "-" * 5
            + "GRID RUN INFO: "
            + f"Finished submitting run {i+1}/{total_num_params}"
            + "-" * 5
        )

    print(f"Submitted {len(jobs)} jobs to slurm")

    if same_gid:
        print(f"Saved {len(jobs)} slurm job ids to {gid_dir}/slurm_job_ids.txt")

    time.sleep(10)
    poll_jobs(jobs)

    if post_process:
        # Post process grid and save xarray to netcdf
        # check if each config in configs has the same "grid_id" and assign it to gid
        if same_gid:
            print(f"Processing and saving grid to csv")
            process_and_save_grid_to_csv(gid, file_root=file_root)
            click.echo(f"Removing {job_ids_file}")
            os.remove(job_ids_file)
        else:
            print(
                f"Configs do not have the same grid_id."
                + " Skipping processing and saving grid to csv"
            )


@sorcerun.command()
@click.argument("grid_id", type=str)
@click.option(
    "--file_root",
    "-f",
    default=FILE_STORAGE_ROOT,
    type=click.Path(file_okay=False),
    help="Root directory for file storage",
)
def grid_to_netcdf(grid_id, file_root):
    save_dir = f"{file_root}/{GRID_OUTPUTS}/{grid_id}"
    # check if there is slurm_job_ids.txt in the grid_id directory
    job_ids_file = os.path.join(save_dir, "slurm_job_ids.txt")
    if os.path.exists(job_ids_file):
        click.echo(f"Slurm job ids found for grid with grid_id {grid_id}.")
        with open(job_ids_file, "r") as file:
            job_ids = file.read().strip().splitlines()
            jobs = [Job(int(job_id)) for job_id in job_ids]
            poll_jobs(jobs)

        # if we made it here, all jobs must have finished,
        # so remove slurm_job_ids.txt
        click.echo(f"Removing {job_ids_file}")
        os.remove(job_ids_file)

    click.echo(f"Processing and saving grid with grid_id {grid_id} to netcdf")
    process_and_save_grid_to_netcdf(grid_id, file_root=file_root)


@sorcerun.command()
@click.argument("grid_id", type=str)
@click.option(
    "--file_root",
    "-f",
    default=FILE_STORAGE_ROOT,
    type=click.Path(file_okay=False),
    help="Root directory for file storage",
)
def grid_to_csv(grid_id, file_root):
    save_dir = f"{file_root}/{GRID_OUTPUTS}/{grid_id}"
    # check if there is slurm_job_ids.txt in the grid_id directory
    job_ids_file = os.path.join(save_dir, "slurm_job_ids.txt")
    if os.path.exists(job_ids_file):
        click.echo(f"Slurm job ids found for grid with grid_id {grid_id}.")
        with open(job_ids_file, "r") as file:
            job_ids = file.read().strip().splitlines()
            jobs = [Job(int(job_id)) for job_id in job_ids]
            poll_jobs(jobs)

        # if we made it here, all jobs must have finished,
        # so remove slurm_job_ids.txt
        click.echo(f"Removing {job_ids_file}")
        os.remove(job_ids_file)

    click.echo(f"Processing and saving grid with grid_id {grid_id} to csv")
    process_and_save_grid_to_csv(grid_id, file_root=file_root)


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


# command to start grid_plotter streamlit app
@sorcerun.command()
def grid_plotter():
    try:
        this_file_path = os.path.abspath(__file__)
        this_dir = os.path.dirname(this_file_path)
        path_to_analysis_file = os.path.join(this_dir, "grid_plotter.py")

        with ExitStack() as stack:
            click.echo("Starting Streamlit app...")
            streamlit_process = subprocess.Popen(
                [
                    "streamlit",
                    "run",
                    path_to_analysis_file,
                ]
            )
            stack.callback(streamlit_process.terminate)
            streamlit_process.wait()
    except subprocess.CalledProcessError as e:
        click.echo(f"Error occurred while running streamlit: {e}")


if __name__ == "__main__":
    sorcerun()
