from sorcerun.git_utils import (
    is_dirty,
    get_repo,
    get_commit_hash,
    get_time_str,
    get_tree_hash,
)

repo = get_repo()
commit_hash = get_commit_hash(repo)
time_str = get_time_str()
main_tree_hash = (get_tree_hash(repo, "main"),)
dirty = is_dirty(repo)
grid_id = (f"{time_str}--{commit_hash}--dirty={dirty}",)

ns = [10, 20, 30]


def make_config(n):
    c = {
        "n": n,
        "commit_hash": commit_hash,
        "main_tree_hash": main_tree_hash,
        "time_str": time_str,
        "dirty": dirty,
        "grid_id": grid_id,
    }
    return c


configs = [make_config(n) for n in ns]
