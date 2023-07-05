import incense
import json
from functools import partial
from pyrsistent import thaw
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from tqdm import tqdm


def get_incense_loader(authfile="sorcerun_auth.json"):
    with open(authfile, "r") as f:
        js = json.loads(f.read())
    db_name = js["db_name"]
    ck = js["client_kwargs"]
    mongo_uri = f"mongodb://{ck['username']}:{ck['password']}@{ck['host']}:{ck['port']}/{db_name}\?authSource=admin"
    # print(mongo_uri)
    return incense.ExperimentLoader(mongo_uri=mongo_uri, db_name=db_name)


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
    setted = {k: set(d[k] for d in ds) for k in ds[0]}
    ks = [k for k in setted if len(setted[k]) > 1]
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
                s = set([e_cfg[a]])

            # union over all the experiments
            coords[a] = coords[a].union(s)
    for k, v in coords.items():
        coords[k] = sorted(list(v))

    coords_without_metric = coords.copy()
    coords_without_metric.pop("metric")
    coords_without_metric.pop("step")

    # create empty xarrays
    shape = tuple(len(coords[a]) for a in axes)
    metric_data = np.empty(shape, dtype=np.float32)
    metric_data.fill(np.nan)
    metrics_arr = xr.DataArray(
        metric_data,
        coords=coords,
        dims=axes,
    )

    shape_without_metric = tuple(len(coords[a]) for a in axes_without_metric)
    exps_data = np.empty(shape_without_metric, dtype=object)
    exps_data.fill(np.nan)
    exps_arr = xr.DataArray(
        exps_data,
        coords=coords_without_metric,
        dims=axes_without_metric,
    )

    # now fill in the metric values
    for e in tqdm(exps[::-1], desc="Filling in metrics"):
        e_cfg_index = squish_dict(thaw(e.config))
        [e_cfg_index.pop(k) for k in exclude_keys]
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
