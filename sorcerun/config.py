import numpy as np
from sorcerun.git_utils import get_exp_info

exp_info = get_exp_info()

n = 1000
d = 100
k = 10
logn_over_k = float(np.log(n) / k)
config = {
    "n": n,
    "d": d,
    "k": k,
    "logn_over_k": logn_over_k,
    "exp_info": exp_info,
}
