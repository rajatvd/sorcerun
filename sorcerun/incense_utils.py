import incense
import json
from functools import partial
from pyrsistent import thaw
import matplotlib.pyplot as plt
import numpy as np


def get_incense_loader(authfile="sorcerun_auth.json"):
    with open(authfile, "r") as f:
        js = json.loads(f.read())
    db_name = js["db_name"]
    ck = js["client_kwargs"]
    mongo_uri = f"mongodb://{ck['username']}:{ck['password']}@{ck['host']}:{ck['port']}/{db_name}\?authSource=admin"
    # print(mongo_uri)
    return incense.ExperimentLoader(mongo_uri=mongo_uri, db_name=db_name)


def filter_by_dict(obj, obj_to_dict=lambda e: e.config, **kwargs):
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
def plot_experiments(
    exps,
    x_key,
    y_func,
    constants={},
    exclude_keys=["seed"],
    short_names={},
    label_extra="",
    plot=True,
    **plot_kwargs,
):
    cfgs = {ex: squish_dict(thaw(ex.config)) for ex in exps}

    filtered = [ex for ex in exps if constants.items() <= cfgs[ex].items()]

    dks = find_differing_keys([cfgs[ex] for ex in filtered])
    dks = [k for k in dks if k not in exclude_keys + [x_key]]

    short = {**{k: k for k in dks}, **short_names}

    datas = {}
    for ex in filtered:
        plot_key = tuple(cfgs[ex][k] for k in dks)
        if plot_key not in datas:
            datas[plot_key] = []
        datas[plot_key].append((cfgs[ex][x_key], y_func(ex)))

    for k, v in datas.items():
        lab = " ".join([f"{short[dk]}={k[i]}" for i, dk in enumerate(dks)])
        lab += label_extra
        dat = np.array(sorted(v, key=lambda x: x[0])).T
        if plot:
            plt.plot(dat[0], dat[1], label=lab, **plot_kwargs)

    return datas
