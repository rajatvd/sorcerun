import time
from git.repo.base import Repo


def get_repo():
    repo = Repo(".", search_parent_directories=True)
    return repo


def get_commit_hash(repo):
    commit_hash = repo.git.rev_parse("HEAD")
    return commit_hash


def is_dirty(repo):
    dirty = repo.is_dirty()
    return dirty


def get_exp_info(short_length=8):
    repo = get_repo()
    short_hash = get_commit_hash(repo)[:short_length]
    time_str = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    exp_info = f"{time_str}-{short_hash}-dirty={is_dirty(repo)}"
    return exp_info
