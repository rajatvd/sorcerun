from sorcerun.git_utils import (
    is_dirty,
    get_repo,
    get_commit_hash,
    get_time_str,
    get_tree_hash,
)

repo = get_repo()

n = 10

config = {
    "n": n,
    "commit_hash": get_commit_hash(repo),
    "main_tree_hash": get_tree_hash(repo, "main"),
    "time_str": get_time_str(),
    "dirty": is_dirty(get_repo()),
}
