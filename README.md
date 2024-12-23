# Sorcerun

Computational experiments can be boiled down to calling a function with some inputs. A common form of analysis is to see how the results of the function varies with different inputs. Sorcerun is a tool built on top of [`sacred`](https://github.com/IDSIA/sacred) that facilitates **logging** each function call to avoid having to repeat experiments that have already been run.

The function is called an **adapter**, and its input is assumed to be a python dictionary, referred to as a **config**. To use sorcerun, provide two python files:

-   `adapter.py` -- it must have a function called `adapter` that has signature
    `adapter(config, _run)`. `_run` is the sacred run object.
-   `config.py` -- it must have a global variable called `config` which is a dictionary.

Run `sorcerun run adapter.py config.py` to call the adapter with the input config as a sacred experiment.

Sorcerun also offers a CLI to help setup and manage a MongoDB observer for sacred.

It also has tools to run **grids** of experiments and then analyze results from experiment grids.

# Todo

-   [x] Add example and documentation (top priority)
    -   [ ] Document the JL example
-   [x] Add ability to add and edit tags to `grid_plotter` to filter experiments
-   [ ] Improve `grid_plotter` with more features for plot customization
-   [ ] Fix the incense version dependency for `FileStorageObserver`
-   [ ] Cleaner source file and other meta info tracking
