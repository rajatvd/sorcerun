from setuptools import setup, find_packages

setup(
    name="sorcerun",
    version="0.2.13",
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
    long_description="Sorcerun is a command-line interface (CLI) designed to streamline the execution and management of computational experiments. It provides built-in support for MongoDB and Sacred, simplifying experiment setup and deployment. Users can configure experiments with a single adapter function, while Sorcerun handles running, logging, and authentication. Additionally, the CLI allows for easy management of MongoDB servers and integrates with the OmniBoard web dashboard for tracking and visualization. Sorcerun aims to facilitate a more efficient experiment lifecycle for researchers, data scientists, and engineers.",
)
