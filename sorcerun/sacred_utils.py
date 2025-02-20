from .globals import AUTH_FILE, RUNS_DIR, FILE_STORAGE_ROOT
from .git_utils import get_repo

from sacred import Experiment, SETTINGS
import pymongo
import traceback
from sacred.observers import MongoObserver, FileStorageObserver
from sacred.utils import apply_backspaces_and_linefeeds
import importlib
import json
import sys
import os
import cProfile
import subprocess

SETTINGS.CAPTURE_MODE = "sys"


def load_python_module(python_file, force_reload=False):
    file_dir = os.path.dirname(os.path.abspath(python_file))
    file_name = os.path.basename(python_file).replace(".py", "")

    sys.path.insert(0, file_dir)
    module = importlib.import_module(file_name)
    if force_reload:
        importlib.reload(module)
    sys.path.pop(0)

    return module


def run_sacred_experiment(
    adapter_func,
    config,
    auth_path=AUTH_FILE,
    use_mongo=True,
    file_storage_root=FILE_STORAGE_ROOT,
    profile=True,
):
    # if file_storage_root is not an absolute path, prefix the current git repo root
    if not os.path.isabs(file_storage_root):
        repo = get_repo()
        if repo is None:
            print(
                f"WARNING: Could not get git repo. Using current working directory as file storage root"
            )
            file_storage_root = os.path.join(os.getcwd(), file_storage_root)
        else:
            file_storage_root = os.path.join(repo.working_dir, file_storage_root)

    experiment_name = getattr(adapter_func, "experiment_name", "sorcerun_experiment")
    ex = Experiment(experiment_name)
    ex.captured_out_filter = apply_backspaces_and_linefeeds

    # Read auth_data from auth_path
    if use_mongo:
        if os.path.exists(auth_path):
            with open(auth_path, "r") as f:
                auth_data = json.load(f)

            atlas = auth_data.get("atlas_connection_string", 0)
            url = (
                (
                    atlas
                    if atlas != 0
                    else f"mongodb://{auth_data['client_kwargs']['username']}:{auth_data['client_kwargs']['password']}@{auth_data['client_kwargs']['host']}:{auth_data['client_kwargs']['port']}"
                ),
            )
            try:
                client = pymongo.MongoClient(url)
                client.server_info()
                observer = MongoObserver(
                    # url=url,
                    client=client,
                    db_name=auth_data["db_name"],
                )

                ex.observers.append(observer)
            except Exception as e:
                traceback.print_exc()
                print(
                    f"WARNING: Failed to connect to MongoDB at {url} with above exception. Not adding mongo observer"
                )
        else:
            print(
                f"WARNING: auth file at {auth_path} does not exist. Not adding mongo observer"
            )
    else:
        print("WARNING: Not using mongo observer (use_mongo=False was passed)")

    runs_dir = os.path.join(file_storage_root, RUNS_DIR)
    os.makedirs(runs_dir, exist_ok=True)
    ex.observers.append(FileStorageObserver.create(runs_dir))
    ex.add_config(config)

    @ex.main
    def run_experiment(_config, _run):
        _run.info["info"] = "info-entry"
        if profile:
            with cProfile.Profile() as pr:
                result = adapter_func(_config, _run)
                pr.dump_stats(f"{runs_dir}/{_run._id}/profile.prof")

            # generate flamegraph using flameprof and flamegraph.pl
            try:
                subprocess.run(
                    f"flameprof --format=log {runs_dir}/{_run._id}/profile.prof "
                    + f"| flamegraph.pl > {runs_dir}/{_run._id}/profile.svg",
                    shell=True,
                )
            except Exception as e:
                traceback.print_exc()
                print(
                    f"WARNING: Failed to generate flamegraph with above exception."
                    + " Not generating flamegraph"
                )
        else:
            result = adapter_func(_config, _run)
        return result

    r = ex.run()
    return r


class DummyRun:
    def __init__(self):
        pass

    def to_dict(self):
        pass

    def log_scalar(self, key, value, step=0):
        pass

    def add_artifact(self, filename, name):
        pass
