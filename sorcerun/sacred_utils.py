from sacred import Experiment
import traceback
from sacred.observers import MongoObserver
import importlib
import json
from .globals import AUTH_FILE
import sys
import os


def load_python_module(python_file):
    # spec = importlib.util.spec_from_file_location("adapter_module", python_file)
    # adapter_module = importlib.util.module_from_spec(spec)
    # spec.loader.exec_module(adapter_module)

    file_dir = os.path.dirname(os.path.abspath(python_file))
    file_name = os.path.basename(python_file).replace(".py", "")

    sys.path.insert(0, file_dir)
    module = importlib.import_module(file_name)
    sys.path.pop(0)

    return module


def run_sacred_experiment(adapter_func, config, auth_path=AUTH_FILE):
    experiment_name = getattr(adapter_func, "experiment_name", "sorcerun_experiment")
    ex = Experiment(experiment_name)

    # Read auth_data from auth_path
    if os.path.exists(auth_path):
        with open(auth_path, "r") as f:
            auth_data = json.load(f)

        atlas = auth_data.get("atlas_connection_string", 0)
        url = (
            atlas
            if atlas != 0
            else f"mongodb://{auth_data['client_kwargs']['username']}:{auth_data['client_kwargs']['password']}@{auth_data['client_kwargs']['host']}:{auth_data['client_kwargs']['port']}",
        )
        observer = MongoObserver(
            url=url,
            db_name=auth_data["db_name"],
        )

        ex.observers.append(observer)
    else:
        print(
            f"WARNING: auth file at {auth_path} does not exist. Not adding mongo observer"
        )

    ex.add_config(config)

    @ex.main
    def run_experiment(_config, _run):
        result = adapter_func(_config, _run)
        return result

    try:
        ex.run()
    except:
        traceback.print_exc()
