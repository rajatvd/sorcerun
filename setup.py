from setuptools import setup, find_packages

setup(
    name="sorcerun",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "click",
        "sacred @ git+https://github.com/rajatvd/sacred.git",
        "pymongo",
    ],
    entry_points="""
        [console_scripts]
        sorcerun=sorcerun_package.cli:sorcerun
    """,
    long_description="Sorcerun long description",
)
