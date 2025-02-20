def adapter(config, _run):
    n = config["n"]

    for i in range(n):
        _run.log_scalar("i", i)
        _run.log_scalar("i_squared", i**2)
        _run.log_scalar("i_cubed", i**3)

    return 0


adapter.experiment_name = "sample_experiment"

if __name__ == "__main__":
    from sorcerun.cli import sorcerun_run
    from sorcerun.git_utils import get_repo

    ROOT = get_repo().working_dir
    sorcerun_run(f"{ROOT}/main/main.py", f"{ROOT}/main/config.py")
