import time
import numpy as np
from git.repo.base import Repo

repo = Repo(".", search_parent_directories=True)
dirty = repo.is_dirty()
commit_hash = repo.git.rev_parse("HEAD")
short_length = 8
short_hash = commit_hash[:short_length]
time_str = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
exp_info = f"{time_str}-{short_hash}-dirty={dirty}"

n = 1000
d = 100
k = 10
logn_over_k = float(np.log(n) / k)
config = {
    "n": n,
    "d": d,
    "k": k,
    "logn_over_k": logn_over_k,
    "exp_info": exp_info,
}
