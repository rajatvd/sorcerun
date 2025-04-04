from setuptools import setup, find_packages
import os

os.chmod("scripts/flamegraph.pl", 0o755)


setup(
    name="sorcerun",
    version="0.5.11",
    packages=find_packages(),
    install_requires=[
        "click",
        # "sacred @ git+https://github.com/rajatvd/sacred.git",
        "sacred",
        "pymongo",
        "pyyaml",
        "scikit-learn",
        "incense",
        # "incense @ git+https://github.com/rajatvd/incense.git",
        "xarray",
        "tqdm",
        "streamlit",
        "ipdb",
        "prettytable",
        "simple_slurm",
        "pandas",
        "pyfzf",
        "flameprof",
    ],
    scripts=["scripts/flamegraph.pl"],
    entry_points="""
        [console_scripts]
        sorcerun=sorcerun.cli:sorcerun
    """,
    long_description="Computational experiments can be boiled down to calling a function with some inputs. A common form of analysis is to see how the results of the function varies with different inputs. Sorcerun is a tool built on top of [`sacred`](https://github.com/IDSIA/sacred) that facilitates **logging** each function call to avoid having to repeat experiments that have already been run.",
)
