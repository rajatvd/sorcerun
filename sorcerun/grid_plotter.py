from numpy import squeeze
from globals import GRID_OUTPUTS
import itertools
import os
import xarray as xr
import matplotlib.pyplot as plt
import streamlit as st

st.title("Grid Plotter")
# show current working directory
working_dir = os.getcwd()
st.write(f"Current working directory: `{working_dir}`")

st.title("Settings")


# Extract all grid ids (they are the names of the subdirectories in GRID_OUTPUTS)
grid_ids = [
    f for f in os.listdir(GRID_OUTPUTS) if os.path.isdir(os.path.join(GRID_OUTPUTS, f))
]

# Select a grid id
grid_id = st.selectbox("Choose a Grid ID", grid_ids)


# Load the netcdf file for the selected grid id as an xarray
grid_output_dir = os.path.join(GRID_OUTPUTS, grid_id)
netcdf_file = os.path.join(grid_output_dir, f"{grid_id}.nc")
data = xr.open_dataarray(netcdf_file)

# get dims with more than 1 coordinate
dims = sorted([dim for dim in data.dims if len(data[dim]) > 1])

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
    dim: str(data.coords[dim].values)
    if len(str(data.coords[dim].values)) < MAX_LEN
    else str(data.coords[dim].values)[: MAX_LEN // 2]
    + "..."
    + str(data.coords[dim].values)[-MAX_LEN // 2 :]
    for dim in dims
}

st.subheader("Dimensions with more than 1 coordinate value")
st.write("Select a reduction option for each dimension")
# create a dictionary of reduction options for each dimension
# if the dim is `repeat`, then the default reduction option is `mean` by default
reduce_options_dict = {
    dim: st.radio(
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
# Choose an x and y axis from both dimensions and metrics
with st.container():
    col1x, col2x = st.columns(2)
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

    col1y, col2y = st.columns(2)
    with col1y:
        y_axis = st.selectbox("Y axis", metric_names)
    with col2y:
        st.text("")
        st.text("")
        log_y = st.checkbox("Log scale y axis", value=False)
# Remaining dims
remaining_dims = sorted(list(set(new_dims) - set([x_axis, y_axis])))


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


# Boolean on whether to save the plots
save_plots = st.checkbox("Save plots", value=False)

if save_plots:
    # Select a save type (png, eps, pdf)
    save_type = st.selectbox("Save type", ["png", "eps", "pdf"])
    save_dir = f"figures/{grid_id}/{save_type}"
    st.write(f"Saving plots to: `{save_dir}`")
    os.makedirs(save_dir, exist_ok=True)


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
    st.write(f"Plotting `{x_axis}` vs `{y_axis}` for each group of `{other_dims}`")

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
        )
        xarr = out[group]

        fig, ax = plt.subplots()
        plt.title(title)
        # use itertools product to iterate over all coordinate combinations of dims_used_in_plot
        for coord in itertools.product(
            *[xarr.coords[dim].values for dim in dims_used_in_plot]
        ):
            d = {dim: coord[i] for i, dim in enumerate(dims_used_in_plot)}
            y = xarr.loc[d].squeeze()
            label = ", ".join([f"{k}={v}" for k, v in d.items()])
            plt.plot(x, y, label=label)

        if log_x:
            plt.xscale("log")
        if log_y:
            plt.yscale("log")
        plt.ylabel(y_axis)
        plt.xlabel(x_axis)
        plt.legend()

        # display plot in streamlit
        st.write(f"Plot {i+1}: {title}")
        st.pyplot(fig)
        if save_plots:
            plt.savefig(f"{save_dir}/{i:03d}--{title}.{save_type}")
