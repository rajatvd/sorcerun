from setuptools import setup, find_packages

setup(
    name="sorcerun",
    version="0.4.7",
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
        "pyfzf",
    ],
    entry_points="""
        [console_scripts]
        sorcerun=sorcerun.cli:sorcerun
    """,
    long_description="Computational experiments can be boiled down to calling a function with some inputs. A common form of analysis is to see how the results of the function varies with different inputs. Sorcerun is a tool built on top of [`sacred`](https://github.com/IDSIA/sacred) that facilitates **logging** each function call to avoid having to repeat experiments that have already been run.",
)
