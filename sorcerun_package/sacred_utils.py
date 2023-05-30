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


def run_sacred_experiment(adapter_func, config, auth_path=AUTH_FILE):
    experiment_name = getattr(adapter_func, "experiment_name", "sorcerun_experiment")
    ex = Experiment(experiment_name)

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

    ex.add_config(config)

    @ex.main
    def run_experiment(_config, _run):
        result = adapter_func(_config, _run)
        return result

    ex.run()
