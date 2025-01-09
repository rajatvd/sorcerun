import time
from git.repo.base import Repo
from .globals import TIME_FORMAT


def get_repo():
    try:
        repo = Repo(".", search_parent_directories=True)
    except Exception as e:
        print(f"An error occurred while trying to get repo: {e}")
        repo = None
    return repo


def get_commit_hash(repo):
    commit_hash = repo.git.rev_parse("HEAD")
    return commit_hash


def is_dirty(repo):
    dirty = repo.is_dirty()
    return dirty


def get_time_str():
    time_str = time.strftime(TIME_FORMAT, time.localtime())
    return time_str


def get_exp_info(short_length=8):
    repo = get_repo()
    short_hash = get_commit_hash(repo)[:short_length]
    time_str = get_time_str()
    exp_info = f"{time_str}-{short_hash}-dirty={is_dirty(repo)}"
    return exp_info


# %%
def get_tree_hash(repo, dir_path):
    try:
        assert not repo.bare, "The repository is bare and has no working tree."

        # Get the current commit
        head_commit = repo.head.commit

        # Get the tree object for the current commit
        tree = head_commit.tree

        # Traverse the tree to find the subdirectory
        tree_obj = tree / dir_path

        return tree_obj.hexsha
    except KeyError:
        print(
            f"Directory '{dir_path}' does not exist in the repository {repo.working_dir}"
        )
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    repo = get_repo()
    tree_hash = get_tree_hash(repo, "sorcerun")
    print(tree_hash)
