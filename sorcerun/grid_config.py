import numpy as np
import itertools
import time
from git.repo.base import Repo

repo = Repo(".", search_parent_directories=True)
dirty = repo.is_dirty()
commit_hash = repo.git.rev_parse("HEAD")
short_length = 8
short_hash = commit_hash[:short_length]
time_str = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
extra = "jlTest"
grid_id = f"{time_str}_{extra}_{short_hash}_dirty={dirty}"

ns = (np.logspace(1, 3, 20, dtype=int)).tolist()
ds = (np.logspace(1, 3, 3, dtype=int)).tolist()
ks = (np.logspace(1, 3, 20, dtype=int)).tolist()
num_repeats = 10

grid_config = {
    "n": ns,
    "d": ds,
    "k": ks,
    "repeat": list(range(num_repeats)),
    "grid_id": [grid_id],
}


configs = []

for v in itertools.product(*grid_config.values()):
    config = dict(zip(grid_config, v))

    config["logn_over_k"] = float(np.log(config["n"])) / float(config["k"])

    configs.append(config)
