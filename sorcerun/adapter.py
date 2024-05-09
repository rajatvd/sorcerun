# experimentally verify the JL lemma
from sorcerun.sacred_utils import DummyRun

import numpy as np


def adapter(config, _run):
    n = config["n"]
    d = config["d"]
    k = config["k"]

    # generate n points in d dimensions on the unit sphere
    X = np.random.randn(d, n)
    norms = np.linalg.norm(X, axis=0)
    X /= norms

    # generate a Gaussian sketch matrix of size k x d
    S = np.random.randn(k, d) / np.sqrt(k)

    # sketch the data
    Y = S @ X

    # measure distortion for each data point
    new_norms = np.linalg.norm(Y, axis=0)

    distortions = np.abs(new_norms - 1)

    _run.log_scalar("mean_distortion", distortions.mean())
    _run.log_scalar("max_distortion", distortions.max())

    output = (
        f"mean distortion: {distortions.mean()}, max distortion: {distortions.max()}"
    )
    return output


adapter.experiment_name = "jl_lemma_test"

if __name__ == "__main__":
    from config import config

    print(adapter(config, DummyRun()))
