# %%
from sorcerun.git_utils import get_tree_hash, get_commit_hash, get_repo, freeze_notebook
import sys

# %%
REPO = get_repo()
if REPO is None:
    raise Exception("Not in a git repository")
sys.path.append(f"{REPO.working_dir}/main")
# %% the following lines will be replaced when the notebook is frozen
COMMIT_HASH = get_commit_hash(REPO)
MAIN_TREE_HASH = get_tree_hash(REPO, "main")
# %%

# ... perform notebook things

# %% freeze the notebook
freeze_notebook(f"plot.py", REPO, COMMIT_HASH, MAIN_TREE_HASH)
