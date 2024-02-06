from setuptools import setup, find_packages

setup(
    name="sorcerun",
    version="0.2.14",
    packages=find_packages(),
    install_requires=[
        "click",
        # "sacred @ git+https://github.com/rajatvd/sacred.git",
        "sacred==0.8.4",
        "pymongo",
        "pyyaml",
        "scikit-learn",
        "incense",
        "xarray",
        "tqdm",
    ],
    entry_points="""
        [console_scripts]
        sorcerun=sorcerun.cli:sorcerun
    """,
    long_description="Computational experiments can be boiled down to calling a function with some inputs. A common form of analysis is to see how the results of the function varies with different inputs. Sorcerun is a tool built on top of [`sacred`](https://github.com/IDSIA/sacred) that facilitates **logging** each function call to avoid having to repeat experiments that have already been run.",
)
