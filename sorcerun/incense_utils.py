from .globals import GRID_OUTPUTS, RUNS_DIR, FILE_STORAGE_ROOT
from pyfzf.pyfzf import FzfPrompt
from collections import defaultdict
import incense
import os
import json
from functools import partial
from pyrsistent import thaw
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from tqdm import tqdm
from pathlib import Path
from prettytable import PrettyTable
import pandas as pd

FILESTORAGE_SPECIAL_DIRS = ["_sources", "_resources"]


# %%
def get_incense_loader(authfile="sorcerun_auth.json"):
    with open(authfile, "r") as f:
        js = json.loads(f.read())
    db_name = js["db_name"]
    ck = js["client_kwargs"]
    mongo_uri = f"mongodb://{ck['username']}:{ck['password']}@{ck['host']}:{ck['port']}/{db_name}\?authSource=admin"
    return incense.ExperimentLoader(mongo_uri=mongo_uri, db_name=db_name)


def load_filesystem_expts_by_config_keys(
    runs_dir=f"{FILE_STORAGE_ROOT}/{RUNS_DIR}",
    **kwargs,
):
    runs_dir = Path(runs_dir)
    configs = {
        run_dir.name: incense.experiment._load_json_from_path(run_dir / "config.json")
        for run_dir in runs_dir.iterdir()
        if run_dir.name not in FILESTORAGE_SPECIAL_DIRS
    }

    # kwargs = {"grid_id": "2024-02-27-19-34-08"}

    ids = list(
        filter(
            partial(
                filter_by_dict,
                obj_to_dict=lambda i: squish_dict(thaw(configs[i])),
                **kwargs,
            ),
            configs.keys(),
        )
    )

    expts = [
        incense.experiment.FileSystemExperiment.from_run_dir(runs_dir / i) for i in ids
    ]

    return expts


def filter_by_dict(obj, obj_to_dict=lambda e: squish_dict(thaw(e.config)), **kwargs):
    d = obj_to_dict(obj)
    out = True
    for k, v in kwargs.items():
        if d.get(k, None) == None:
            return False
        out = out and d[k] == v
    return out


def filter_by_config(exps, **kwargs):
    return filter(partial(filter_by_dict, **kwargs), exps)


# %%
def find_differing_keys(ds):
    # find keys that have differing values in the list of dictionaries
    # if a value is a list, convert to tuple

    ranges = defaultdict(set)
    for d in ds:
        for k, v in d.items():
            if type(v) == list:
                v = tuple(v)
            ranges[k].add(v)

    ks = [k for k in ranges if len(ranges[k]) > 1]

    # setted = {k: set(d[k] for d in ds) for k in ds[0]}
    # ks = [k for k in setted if len(setted[k]) > 1]
    return ks


# %%
def squish_dict(d):
    """Flatten a nested dictionary into a single dictionary.

    Nested keys are indexed with a dot. For example,

    d = {
        'a': 1,
        'b': {
            'c': 2,
            'd': 3,
            'blah': {
                'foo': 67,
                'bar': 'no'
            }
        },
        'e': 'lol'
    }

    becomes

    {
        'a': 1,
        'b.c': 2,
        'b.d': 3,
        'b.blah.foo': 67,
        'b.blah.bar': 'no',
        'e': 'lol'
    }

    """
    ks = list(d.keys())
    for k in ks:
        v = d[k]
        assert type(k) == str, "cannot squish non-string keys"
        if type(v) != dict:
            continue

        squished = squish_dict(v)
        for sk, sv in squished.items():
            d[k + "." + sk] = sv

        del d[k]
    return d


# %%
def unsquish_dict(d):
    """Inflate a flattened dictionary back into a nested dictionary.

    Nested keys are indexed with a dot. For example,

    d = {
        'a': 1,
        'b.c': 2,
        'b.d': 3,
        'b.blah.foo': 67,
        'b.blah.bar': 'no',
        'e': 'lol'
    }

    becomes

    {
        'a': 1,
        'b': {
            'c': 2,
            'd': 3,
            'blah': {
                'foo': 67,
                'bar': 'no'
            }
        },
        'e': 'lol'
    }

    """
    result = {}
    for k, v in d.items():
        assert type(k) == str, "cannot unsquish non-string keys"
        keys = k.split(".")
        assert len(keys) > 0, "cannot unsquish keys with no content"

        # Start from the top-level dictionary and gradually drill down
        current_level = result
        for sub_key in keys[:-1]:
            if sub_key not in current_level:
                current_level[sub_key] = {}
            current_level = current_level[sub_key]
            assert isinstance(
                current_level, dict
            ), "non-dict intermediate level detected"

        # By this point, current_level is the dictionary where the value should be placed
        final_key = keys[-1]
        current_level[final_key] = v
    return result


# %%
def exps_to_xarray(exps, exclude_keys=["seed"]):
    """Convert a list of incense experiments to two xarrays.

    :param exps: input list of experiments
    :param exclude_keys: config keys to exclude

    Returns: tuple (exps_arr, metrics_arr)
    Both are xarrays.

    exps_arr has dims given by the union of squished config keys over all experiments.
    The corresponding coords are also the union over all possible values of the
    corresponding config key. The value of each entry is the incense Experiment object.

    metrics_arr is the same as exps_arr, with two additional dims: "metric" and "step".
    The value of each entry is now the value of the metric at step "step" for each
    experiment.
    """
    # info about tuple/list valued coordinates:
    # First of all, when extracting the coordinates, we need to convert list values to tuples
    # because lists are unhashable and we use set unioning to get the unique values of each
    # coordinate.
    # Second, if you pass a list of tuples as coordinate values to xarray, it doesnt treat
    # it as a 1D coordinate, but as a 2D coordinate. This is not what we want. So we convert
    # the list of tuples to a numpy array of objects, which xarray treats as a 1D coordinate.

    # Finally, when saving this to netcdf, xarray didnt like tuple values as coordinates
    # either, so we just convert them to strings, only for saving to netcdf.
    # This change is not in this function, but in process_and_save_grid_to_netcdf.

    # get set of axis keys from config
    e_cfg_keys = set()
    for e in exps:
        e_cfg_keys = e_cfg_keys.union(set(squish_dict(thaw(e.config)).keys()))
    axes_without_metric = list(e_cfg_keys - set(exclude_keys))
    axes = axes_without_metric + ["metric", "step"]
    print(f"axes={axes}")

    e = exps[1]
    # get coordinates of each axis key in the grid
    # by looping through every experiment and taking the union of the coord set
    coords = {a: set() for a in axes}
    for e in tqdm(exps, desc="Extracting coords"):
        e_cfg = squish_dict(thaw(e.config))
        for a in axes:
            if a == "metric":
                # union all the metrics
                s = set(e.metrics.keys())
            elif a == "step":
                # union over the possible steps for all metrics for this exp
                s = set()
                for v in e.metrics.values():
                    s = s.union(list(v.index))
            else:
                val = e_cfg[a]
                # both list and np.array are not hashable, so convert to tuple
                if type(val) == list:
                    val = tuple(val)
                s = set([val])

            # union over all the experiments
            coords[a] = coords[a].union(s)
    for k, v in coords.items():
        if any(type(x) == tuple for x in v):
            vl = list(v)
            # now use np.array because xarray doesn't like lists of tuples
            vals = np.empty(shape=(len(vl),), dtype=object)
            for i, val in enumerate(vl):
                vals[i] = val
        else:
            vals = sorted(list(v))
        coords[k] = vals

    # remove axes of size 1 (except metric and step)

    axes_copy = axes.copy()
    size_one_axes = []
    for a in axes_copy:
        if a == "metric" or a == "step":
            continue
        if len(coords[a]) == 1:
            print(f"Removing axis {a} because it has size 1")
            axes.remove(a)
            axes_without_metric.remove(a)
            coords.pop(a)
            size_one_axes.append(a)

    # print out the axes and their sizes
    t = PrettyTable(["Axis", "Size"])
    for a in axes:
        t.add_row([a, len(coords[a])])
    t.align = "l"
    print(t)

    coords_without_metric = coords.copy()
    coords_without_metric.pop("metric")
    coords_without_metric.pop("step")

    # create empty xarrays
    shape = tuple(len(coords[a]) for a in axes)

    # metric data should have same dtype as the metric values
    metric_dtype = np.float64
    metric_data = np.empty(shape, dtype=metric_dtype)
    metric_data.fill(np.nan)
    metrics_arr = xr.DataArray(
        metric_data,
        coords=coords,
        dims=axes,
        name="metrics",
    )

    shape_without_metric = tuple(len(coords[a]) for a in axes_without_metric)
    exps_data = np.empty(shape_without_metric, dtype=object)
    exps_data.fill(np.nan)
    exps_arr = xr.DataArray(
        exps_data,
        coords=coords_without_metric,
        dims=axes_without_metric,
        name="experiments",
    )

    # now fill in the metric values
    for e in tqdm(exps[::-1], desc="Filling in metrics"):
        e_cfg_index = squish_dict(thaw(e.config))
        [e_cfg_index.pop(k) for k in exclude_keys]
        [e_cfg_index.pop(k) for k in size_one_axes]

        # convert values of type list to tuple
        for k, v in e_cfg_index.items():
            if type(v) == list:
                e_cfg_index[k] = tuple(v)

        exps_arr.loc[e_cfg_index] = e

        # get the x_arr of this experiment
        e_arr = metrics_arr.sel(**e_cfg_index)

        for k, v in e.metrics.items():
            # fill in each metric into the x_arr
            # Note that we are only filling in values of v.index, and this will
            # always be a subset of the coordspace of step since we did the unioning
            # before.
            e_arr.loc[dict(metric=k, step=v.index)] = v.values

    return exps_arr, metrics_arr


def print_file_size(file_path):
    file_info = os.stat(file_path)
    size_in_bytes = file_info.st_size

    if size_in_bytes < 1024:
        print(f"The size of '{file_path}' is: {size_in_bytes} bytes")
    elif size_in_bytes >= 1024 and size_in_bytes < 1024**2:
        print(f"The size of '{file_path}' is: {size_in_bytes / 1024:.2f} KB")
    elif size_in_bytes >= 1024**2 and size_in_bytes < 1024**3:
        print(f"The size of '{file_path}' is: {size_in_bytes / 1024**2:.2f} MB")
    else:
        print(f"The size of '{file_path}' is: {size_in_bytes / 1024**3:.2f} GB")


def process_and_save_grid_to_netcdf(gid, file_root=FILE_STORAGE_ROOT):
    grid_exps = load_filesystem_expts_by_config_keys(
        grid_id=gid,
        runs_dir=os.path.join(file_root, RUNS_DIR),
    )

    print(f"Found {len(grid_exps)} experiments with grid_id {gid}")

    grid_exps_xr, grid_metrics_xr = exps_to_xarray(grid_exps)
    metrics_reduced_xr = grid_metrics_xr

    save_dir = f"{file_root}/{GRID_OUTPUTS}/{gid}"
    os.makedirs(save_dir, exist_ok=True)

    netcdf_save_path = f"{save_dir}/{gid}.nc"
    print(f"Saving to {netcdf_save_path}")

    # convert coordinate values that are tuples to strings to avoid serialization issues
    old_coords = [(k, v) for k, v in metrics_reduced_xr.coords.items()]
    for k, v in old_coords:
        if any(type(x) == tuple for x in v.values):
            print(f"Converting coordinate values of {k} to str")
            metrics_reduced_xr.coords[k] = [str(x) for x in v.values]

    metrics_reduced_xr.to_netcdf(netcdf_save_path)

    print_file_size(netcdf_save_path)


# %%
def xarray_to_csv(da, csv_filename):
    """
    Convert an xarray DataArray to a CSV file, removing NaN values.

    Parameters:
    da (xarray.DataArray): The input DataArray
    csv_filename (str): The name of the output CSV file

    Returns:
    None
    """
    # Step 1: Convert to pandas DataFrame
    df = da.to_dataframe()

    # Step 2: Drop NaN values
    df_clean = df.dropna()

    # Step 3: Reset index to create columns for each coordinate
    df_clean_reset = df_clean.reset_index()

    # Step 4: Save to CSV
    df_clean_reset.to_csv(csv_filename, index=False)

    print_file_size(csv_filename)

    return df_clean_reset


# %%
def csv_to_xarray(csv_filename, value_column):
    """
    Convert a CSV file to an xarray DataArray,
    treating all columns except the value column as coordinates.
    The DataArray is named after the value column.

    Parameters:
    csv_filename (str): The name of the input CSV file
    value_column (str): The name of the column containing the data values

    Returns:
    xarray.DataArray: The resulting DataArray
    """
    df = pd.read_csv(csv_filename)

    coord_columns = [col for col in df.columns if col != value_column]

    coords = {col: sorted(df[col].unique()) for col in coord_columns}

    shape = tuple(len(coords[col]) for col in coord_columns)
    data = np.full(shape, np.nan)

    for _, row in df.iterrows():
        index = tuple(coords[col].index(row[col]) for col in coord_columns)
        data[index] = row[value_column]

    da = xr.DataArray(data, coords=coords, dims=coord_columns, name=value_column)

    return da


# %%
def process_and_save_grid_to_csv(gid, file_root=FILE_STORAGE_ROOT):
    grid_exps = load_filesystem_expts_by_config_keys(
        grid_id=gid,
        runs_dir=os.path.join(file_root, RUNS_DIR),
    )

    print(f"Found {len(grid_exps)} experiments with grid_id {gid}")

    grid_exps_xr, grid_metrics_xr = exps_to_xarray(grid_exps)

    save_dir = f"{file_root}/{GRID_OUTPUTS}/{gid}"
    os.makedirs(save_dir, exist_ok=True)

    csv_filename = f"{save_dir}/{gid}.csv"
    print(f"Saving to {csv_filename}")

    # convert coordinate values that are tuples to strings to avoid serialization issues
    old_coords = [(k, v) for k, v in grid_metrics_xr.coords.items()]
    for k, v in old_coords:
        if any(type(x) == tuple for x in v.values):
            print(f"Converting coordinate values of {k} to str")
            grid_metrics_xr.coords[k] = [str(x) for x in v.values]

    df = xarray_to_csv(grid_metrics_xr, csv_filename)
    return df


# %%
def get_latest_single_and_grid_exps(exps):
    """Parse list of experiments to get the latest
    single experiment and grid of experiments
    (a grid of exps is assumed to have the
    same time_str for all exps in the grid).

    :param exps: list of incense experiments

    Returns: tuple (single_exp, grid_exps)

    If no single experiment is found, single_exp is None.
    If no grid experiments are found, grid_exps is an empty list.
    """
    time_str_to_exps = {}
    for exp in exps:
        time_str = exp.config.time_str
        if time_str not in time_str_to_exps:
            time_str_to_exps[time_str] = []
        time_str_to_exps[time_str].append(exp)
    sorted_time_strs = sorted(time_str_to_exps.keys())[::-1]
    single_exp_time_str = None
    grid_time_str = None
    for time_str in sorted_time_strs:
        if len(time_str_to_exps[time_str]) == 1:
            single_exp_time_str = (
                time_str if single_exp_time_str is None else single_exp_time_str
            )
        else:
            grid_time_str = time_str if grid_time_str is None else grid_time_str

        if single_exp_time_str is not None and grid_time_str is not None:
            break

    single_exp = time_str_to_exps.get(single_exp_time_str, [None])[0]
    grid_exps = time_str_to_exps.get(grid_time_str, [])
    return single_exp, grid_exps


# %%
def dict_to_fzf_friendly_str(d):
    return " ".join([f"{k}:{v}" for k, v in d.items()]) + " "


# this class is still WIP
class ExpsSlicer:
    def __init__(self, exps, runs_dir=RUNS_DIR, exclude_keys=["seed"]):
        self.exps = exps
        self.runs_dir = runs_dir
        self.dicts = [squish_dict(thaw(e.config)) for e in self.exps]
        for k in exclude_keys:
            [d.pop(k) for d in self.dicts]

        self.ks = find_differing_keys(self.dicts)
        dicts_with_only_diff_keys = [
            {k: d.get(k, None) for k in self.ks} for d in self.dicts
        ]
        ids = [str(e.id) for e in self.exps]
        self.id_to_exp = {i: e for i, e in zip(ids, self.exps)}
        self.dictstrs = [
            f"{i} " + dict_to_fzf_friendly_str(d)
            for i, d in zip(ids, dicts_with_only_diff_keys)
        ]

        self.ranges = defaultdict(set)
        for d in dicts_with_only_diff_keys:
            for k, v in d.items():
                self.ranges[k].add(v)

        self.ranges = {k: sorted(list(v)) for k, v in self.ranges.items()}
        self.ranges_dir = os.path.join(FILE_STORAGE_ROOT, "ranges")
        os.makedirs(self.ranges_dir, exist_ok=True)
        for k, v in self.ranges.items():
            with open(f"{self.ranges_dir}/{k}_range.txt", "w") as f:
                f.write("\n".join(map(str, v)))

        self.fzf = FzfPrompt()

    def fzf_filter(self):
        key = self.fzf.prompt(
            list(self.ks), " --preview 'cat " + f"{self.ranges_dir}/" + "{1}_range.txt'"
        )[0]
        out = self.fzf.prompt(
            self.dictstrs,
            "--multi"
            + " --preview 'cat "
            + f"{self.runs_dir}/"
            + "{1}/cout.txt'"
            + f" --print-query"
            + f" --query \\'{key}:"
            + " --bind enter:select-all+accept",
        )
        query = out[0]
        out_ids = [o.split()[0] for o in out[1:]]
        out_exps = [self.id_to_exp[i] for i in out_ids]
        return ExpsSlicer(out_exps, runs_dir=self.runs_dir)

    def __call__(self, **kwargs):
        if len(kwargs) == 0:
            return self.fzf_filter()
        return ExpsSlicer(
            list(filter_by_config(self.exps, **kwargs)),
            runs_dir=self.runs_dir,
        )

    def __len__(self):
        return len(self.exps)


# %%
if __name__ == "__main__":
    fzf = FzfPrompt()
    gid = fzf.prompt(os.listdir(f"{FILE_STORAGE_ROOT}/{GRID_OUTPUTS}"))[0]
    runs_dir = os.path.join(FILE_STORAGE_ROOT, RUNS_DIR)
    out = load_filesystem_expts_by_config_keys(
        grid_id=gid,
        runs_dir=runs_dir,
    )
    print(len(out))
    exps_arr, metrics_arr = exps_to_xarray(out, exclude_keys=["seed"])

    # product of all the axes sizes
    print(np.prod([len(v) for v in metrics_arr.coords.values()]))

    df = xarray_to_csv(metrics_arr, f"{gid}.csv")
    da = csv_to_xarray(f"{gid}.csv", "metrics")
    err = np.abs(da.data - metrics_arr.data)
    print(np.sum(err[~np.isnan(err)]))

#     slicer = ExpsSlicer(out, runs_dir=runs_dir)
#     e = out[0]
#     print(e._data["captured_out"])
#     vars(e)
#     ans = slicer()()()
