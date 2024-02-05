# Sorcerun

Computational experiments can be boiled down to calling a function with some inputs. A common form of analysis is to see how the results of the function varies with different inputs. Sorcerun is a tool built on top of [`sacred`](https://github.com/IDSIA/sacred) that facilitates **logging** each function call to avoid having to repeat experiments that have already been run.

The function is called an **adapter**, and its input is assumed to be a python dictionary, referred to as a **config**. To use sorcerun, provide two python files:

-   `adapter.py` -- it must have a function called `adapter` that has signature
    `adapter(config, _run)`. `_run` is the sacred run object.
-   `config.py` -- it must have a global variable called `config` which is a dictionary.

Run `sorcerun run adapter.py config.py` to call the adapter with the input config as a sacred experiment.

Sorcerun also offers a CLI to help setup and manage a MongoDB observer for sacred.

It also has tools to run **grids** of experiments and then analyze results from experiment grids.

TODO: add simple example

# TODO

-   [ ] Utilities to forward ports via ssh
-   [x] Grid run utilities via CLI
-   [ ] More template adapters and generate them via CLI
    -   Specifically something that can track STDOUT and log metrics from STDOUT?
-   [ ] Cleaner source file and other meta info tracking
-   [x] General utilities with `incense` -- maybe build `streamlit` app separately?
-   [x] Better logging for the mongod server
-   [ ] Add example and documentation
-   [x] Change description to be simpler -- logged function calls
-   [ ] Improve `grid_plotter` with more features for plot customization
