from sorcerun.sacred_utils import run_sacred_experiment


def adapter(config, _run):
    n = config["n"]

    for i in range(n):
        _run.log_scalar("i", i)
        _run.log_scalar("i_squared", i**2)
        _run.log_scalar("i_cubed", i**3)

    return 0


adapter.experiment_name = "sample_experiment"

if __name__ == "__main__":
    from config import config

    run_sacred_experiment(adapter, config)
