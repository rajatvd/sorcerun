import time
import os
import inspect
from git.repo.base import Repo
from git import Repo, RemoteReference
from .globals import TIME_FORMAT, FILE_STORAGE_ROOT
import sys


# %%
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
def inject_repo_into_sys_path():
    """Inject the repository root into sys.path for module imports.

    TODO: check how this works with git worktrees

    Also returns the path to the repo root.
    """
    repo = get_repo()
    if repo:
        repo_root = repo.working_dir
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
            print(f"Injected {repo_root} into sys.path")
        else:
            print(f"{repo_root} is already in sys.path")
    else:
        print("No repository found to inject into sys.path")

    return repo_root


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
            f"Directory '{dir_path}' does not exist "
            + f"in the repository {repo.working_dir}"
        )
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# %%
def branches_pointing_to(
    repo: Repo,
    commit_sha: str,
    *,
    include_remote: bool = False,
) -> list[str]:
    """
    Return all branch names whose *tip* is exactly the given commit.

    Parameters
    ----------
    repo : git.Repo
        An initialized GitPython repository object.
    commit_sha : str
        Full or abbreviated SHA of the target commit.
    include_remote : bool, optional (default=True)
        If True, remote branches (e.g., 'origin/main') are included.

    Returns
    -------
    list[str]
        Sorted list of branch names pointing to the commit (may be empty).
    """
    try:
        target_commit = repo.commit(commit_sha)
    except Exception:  # BadName, ValueError, etc.
        return []

    refs = list(repo.heads)  # local branches
    if include_remote:
        for remote in repo.remotes:
            refs.extend(remote.refs)  # RemoteReference objects

    # Remove duplicates and keep only refs whose *tip* is the target commit
    branch_names = {
        ref.name
        for ref in refs
        if ref.commit == target_commit
        and (not isinstance(ref, RemoteReference) or include_remote)
    }

    return sorted(branch_names)


# %%
def freeze_notebook(
    filename,
    repo,
    commit_hash,
    **assignments,
):
    """freeze_notebook.

    :param filename: The name of the python file to freeze.
    :param repo: The Git repository object.
    :param commit_hash: The commit hash to use for the freeze.
    :param assignments: A dictionary of variable assignments to replace in the file.
        Assignments should be in the form of {name: value}.
        The lines that start with `name = ` will be replaced with `name = "value"`.
        The value is treated as a string.
    """
    script_path = f"{repo.working_dir}/{filename}"

    base_filename = filename.split("/")[-1]

    branches = branches_pointing_to(repo, commit_hash)

    nice_name = f"{branches[0]}_{commit_hash[:8]}"

    commit = repo.commit(commit_hash)
    commit_time = commit.committed_datetime.strftime(TIME_FORMAT)
    target_dir = (
        f"{repo.working_dir}/{FILE_STORAGE_ROOT}/notebooks/"
        + f"{commit_time}_{nice_name}"
    )
    os.makedirs(target_dir, exist_ok=True)
    target_path = f"{target_dir}/{nice_name}_{base_filename}"

    # Read the current content of the script
    with open(script_path, "r") as f:
        lines = f.readlines()

    # Prepare the replacement lines
    commit_line = f'COMMIT_HASH = "{commit_hash}"\n'

    # Find and replace the target lines
    replaced_commit = False
    replaced_assignments = {name: False for name in assignments.keys()}
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("COMMIT_HASH = "):
            new_lines.append(commit_line)
            replaced_commit = True
        # check if the line starts with assignemnt
        elif any(stripped.startswith(f"{name} = ") for name in assignments.keys()):
            for name, value in assignments.items():
                if stripped.startswith(f"{name} = "):
                    new_lines.append(f'{name} = "{value}"\n')
                    replaced_assignments[name] = True
                    break
        else:
            new_lines.append(line)

    # Check if all lines were found and replaced
    if not replaced_commit:
        raise RuntimeError("COMMIT_HASH assignment line not found")
    if not all(replaced_assignments.values()):
        raise RuntimeError(
            "One or more assignment lines not found: "
            + ", ".join(
                [
                    name
                    for name, replaced in replaced_assignments.items()
                    if not replaced
                ]
            )
        )

    # Write the modified content back to the file
    with open(target_path, "w") as f:
        f.writelines(new_lines)


if __name__ == "__main__":
    repo = get_repo()
    tree_hash = get_tree_hash(repo, "sorcerun")
    print(tree_hash)
