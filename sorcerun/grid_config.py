import numpy as np
import itertools
from sorcerun.git_utils import get_repo, get_time_str, get_commit_hash, is_dirty

repo = get_repo()
dirty = is_dirty(repo)
time_str = get_time_str()
short_hash = get_commit_hash(repo)[:8]

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
