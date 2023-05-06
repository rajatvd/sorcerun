from sacred import Experiment
from sacred.observers import MongoObserver
import importlib
import json
from .globals import AUTH_FILE


def load_adapter_function(python_file):
    spec = importlib.util.spec_from_file_location("adapter_module", python_file)
    adapter_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter_module)
    adapter_func = adapter_module.adapter
    return adapter_func


def run_sacred_experiment(adapter_func, config):
    ex = Experiment("sorcerun_experiment")

    with open(AUTH_FILE, "r") as f:
        auth_data = json.load(f)

    observer = MongoObserver(
        url=f"mongodb://{auth_data['client_kwargs']['username']}:{auth_data['client_kwargs']['password']}@{auth_data['client_kwargs']['host']}:{auth_data['client_kwargs']['port']}",
        db_name=auth_data["db_name"],
    )

    ex.observers.append(observer)

    ex.add_config(config)

    @ex.main
    def run_experiment(_config, _run):
        result = adapter_func(_config, _run)
        _run.result = result

    ex.run()
