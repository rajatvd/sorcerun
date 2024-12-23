from numpy import squeeze
import numpy as np
from sorcerun.globals import GRID_OUTPUTS
import itertools
import os
import xarray as xr
import matplotlib.pyplot as plt
import streamlit as st
import scipy.stats
from sorcerun.incense_utils import csv_to_xarray

st.title("Grid Plotter")
# show current working directory
working_dir = os.getcwd()
st.write(f"Current working directory: `{working_dir}`")

st.title("Settings")

# Checkbox to decide whether to show all grid ids or only the ones with tags
show_all_grids = not st.checkbox("Show only tagged grids", value=False)

# Extract grid ids
name_to_gid = {}
for f in os.listdir(GRID_OUTPUTS):
    if os.path.isdir(os.path.join(GRID_OUTPUTS, f)):
        gid = f
        tags_file = os.path.join(GRID_OUTPUTS, gid, f"{gid}-tags.txt")

        tags = ""
        if os.path.exists(tags_file):
            with open(tags_file, "r") as f:
                tags = f" tags: {f.read().strip()}"

        if show_all_grids or tags:
            name_to_gid[f"{gid}{tags}"] = gid


# Select a grid id
name = st.selectbox("Choose a Grid ID", list(name_to_gid.keys()))
grid_id = name_to_gid[name]

# Add a text box to modify tags for the selected grid id
tags_file = os.path.join(GRID_OUTPUTS, grid_id, f"{grid_id}-tags.txt")
tags = ""
if os.path.exists(tags_file):
    with open(tags_file, "r") as f:
        tags = f.read().strip()

new_tags = st.text_input("Tags", value=tags)

# Add a button to save the tags
if st.button("Save tags"):
    # delete the tags file if the new tags are empty
    if not new_tags:
        if os.path.exists(tags_file):
            os.remove(tags_file)
    else:
        with open(tags_file, "w") as f:
            f.write(new_tags)
    st.rerun()

st.write(f"Selected grid id: `{grid_id}`")


# Load the csv file for the selected grid id as an xarray
grid_output_dir = os.path.join(GRID_OUTPUTS, grid_id)
csv_file = os.path.join(grid_output_dir, f"{grid_id}.csv")

data = csv_to_xarray(csv_file, value_column="metrics")

# get dims with more than 1 coordinate
dims = sorted([dim for dim in data.dims if len(data[dim]) > 1 and dim != "metric"])

# get metric names

# For each axis, have an option to reduce the coordinate by taking mean, max, min or just ignoring it
# Use a radio button to select the reduction option
reduce_options = [
    "don't reduce",
    "mean",
    "max",
    "min",
]


# create a list of strings showing shorted coordinate values
# (if the length of the coordinate is greater than 10, then it is shortened)
MAX_LEN = 100
shortened_coords = {
    dim: (
        str(data.coords[dim].values)
        if len(str(data.coords[dim].values)) < MAX_LEN
        else str(data.coords[dim].values)[: MAX_LEN // 2]
        + "..."
        + str(data.coords[dim].values)[-MAX_LEN // 2 :]
    )
    for dim in dims
}

st.subheader("Dimensions with more than 1 coordinate value")
st.write("Select a reduction option for each dimension")
# create a dictionary of reduction options for each dimension
# if the dim is `repeat`, then the default reduction option is `mean` by default
reduce_options_dict = {
    dim: (
        st.radio(
            f"`{dim}`: {shortened_coords[dim]}",
            reduce_options,
            horizontal=True,
        )
        if dim != "repeat"
        else st.radio(
            f"`{dim}`: {shortened_coords[dim]}",
            reduce_options,
            horizontal=True,
            index=1,
        )
    )
    for dim in dims
}

# apply the reduction to the data
for dim, reduce_option in reduce_options_dict.items():
    if reduce_option == "mean":
        data = data.mean(dim=dim)
    elif reduce_option == "max":
        data = data.max(dim=dim)
    elif reduce_option == "min":
        data = data.min(dim=dim)

# Get the new set of axes
new_dims = [dim for dim in data.dims if len(data[dim]) > 1]

metric_names = list(data["metric"].values)
st.subheader("Metrics")
st.write(metric_names)

st.subheader("Choose axes for each plot")
xlim = None
ylim = None
# Choose an x and y axis from both dimensions and metrics
with st.container():
    # add a column for setting xlim and ylim
    col1x, col2x, col3x, col4x = st.columns(4)
    with col1x:
        x_axis = st.selectbox(
            "X axis",
            new_dims,
            index=new_dims.index("step") if "step" in new_dims else 0,
        )
    with col2x:
        st.text("")
        st.text("")
        log_x = st.checkbox("Log scale x axis", value=False)

    with col3x:
        x_label = st.text_input("X label", value=x_axis)

    with col4x:
        xlim = st.text_input("X limits", value="")
        if xlim:
            xlim = [float(x) for x in xlim.split(",")]

    col1y, col2y, col3y, col4y = st.columns(4)
    # Choose multiple y axes from the metrics
    with col1y:
        y_axes = st.multiselect("Y axis", metric_names)
    with col2y:
        st.text("")
        st.text("")
        log_y = st.checkbox("Log scale y axis", value=False)
    with col3y:
        y_label = st.text_input("Y label", value="metric")
    with col4y:
        ylim = st.text_input("Y limits", value="")
        if ylim:
            ylim = [float(y) for y in ylim.split(",")]

# Remaining dims
remaining_dims = sorted(list(set(new_dims) - set([x_axis, "metric"])))

# Choose a style for the plot
style = st.text_input("Line style", value="o-")

# Choose plot dimensions to include within a single plot
st.subheader("Choose dimensions that are kept fixed in each plot")
fixed_dims_per_plot = st.multiselect(
    "Fixed dims per plot",
    remaining_dims,
)

dims_used_in_plot = sorted(list(set(remaining_dims) - set(fixed_dims_per_plot)))
other_dims = fixed_dims_per_plot
st.write("Dimensions that vary in each plot:")
st.write(dims_used_in_plot)

# Boolean on whether to show regression line slope
show_slope = st.checkbox("Show regression line slope", value=False)

# Boolean on whether to have axis grids
axis_grids = st.checkbox("Show axis grids", value=True)

# Boolean on whether to save the plots
save_plots = st.checkbox("Save plots", value=False)

if save_plots:
    # Select a save type (png, eps, pdf)
    save_type = st.selectbox("Save type", ["png", "eps", "pdf"])
    save_dir = f"figures/{grid_id}/{save_type}"
    st.write(f"Saving plots to: `{save_dir}`")
    os.makedirs(save_dir, exist_ok=True)

# ToDO: auto change ylabel is there is only one metric and dont include that in legend

# Add a button to actually make the plots
# check if other_dims is empty
if not other_dims:
    out = data
    groups = [()]
else:
    out = data.stack(other_dims=other_dims).groupby("other_dims", squeeze=False)
    groups = list(out.groups.keys())

if st.button(f"Make {len(groups)} plots"):
    st.subheader(f"Creating {len(groups)} plots")
    st.write(f"Plotting `{x_axis}` vs `{y_axes}` for each group of `{other_dims}`")

    TITLE_NAME = {k: k for k in other_dims}
    title_keys = other_dims

    x = data.coords[x_axis].values

    for i, group in enumerate(groups):
        title = "--".join(
            [
                f"{TITLE_NAME[key]}={val}"
                for key, val in zip(other_dims, group)
                if key in title_keys
            ]
            + [f"metrics={'-'.join(y_axes)}"]
        )
        xarr = out[group]

        fig, ax = plt.subplots()
        plt.title(title)
        # use itertools product to iterate over all coordinate combinations of dims_used_in_plot
        for coord in itertools.product(
            *[xarr.coords[dim].values for dim in dims_used_in_plot]
        ):
            d = {dim: coord[i] for i, dim in enumerate(dims_used_in_plot)}
            ys = xarr.loc[d]
            for y_axis in y_axes:
                y = ys.loc[dict(metric=y_axis)].squeeze().to_numpy()
                label = ", ".join([f"{k}={v}" for k, v in d.items()])
                if len(y_axes) > 1:
                    label = y_axis + " " + label

                # check if y is all nans or infs, if so, don't plot
                good_inds = np.isfinite(y)

                # dont_plot = y.isnull().all().item() or (y == float("inf")).all().item()
                dont_plot = not np.any(good_inds)
                if not dont_plot:
                    plt.plot(x, y, style, label=label)
                    # add regression line slope
                    if len(x) > 1 and show_slope:
                        x_to_regress = np.log(x) if log_x else x
                        y_to_regress = np.log(y) if log_y else y

                        # remove nans and infs
                        keep_inds = np.isfinite(x_to_regress) & np.isfinite(
                            y_to_regress
                        )
                        x_to_regress = x_to_regress[np.where(keep_inds)]
                        y_to_regress = y_to_regress[np.where(keep_inds)]

                        # slope, intercept = np.polyfit(x_to_regress, y_to_regress, 1)
                        (
                            slope,
                            intercept,
                            r_value,
                            p_value,
                            std_err,
                        ) = scipy.stats.linregress(x_to_regress, y_to_regress)
                        plt.text(
                            x[-1],
                            y[-1],
                            f"Slope: {slope:.7f}, $r^2$: {r_value**2:.7f}",
                            horizontalalignment="right",
                            verticalalignment="top",
                        )

        if log_x:
            plt.xscale("log")
        if log_y:
            plt.yscale("log")
        plt.ylabel(y_label)
        plt.xlabel(x_label)
        if xlim:
            plt.xlim(xlim)
        if ylim:
            plt.ylim(ylim)

        # place legend outside plot to the right using axis
        leg = fig.legend(loc="center left", bbox_to_anchor=(0.92, 0.5))
        # plt.legend()

        if axis_grids:
            plt.grid(True)

        # display plot in streamlit
        if save_plots:
            fig.savefig(
                f"{save_dir}/{i:03d}--{title}.{save_type}",
                bbox_extra_artists=[leg],
                bbox_inches="tight",
            )
        st.write(f"Plot {i+1}: {title}")
        st.pyplot(fig)
