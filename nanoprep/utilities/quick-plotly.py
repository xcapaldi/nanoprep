# -*- coding: utf-8 -*-
""" Quick plotting module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

# import necessary packages
import os
import sys
import csv
import numpy as np
import plotly.graph_objects as go

# this will allow dragging and dropping csv's to plot on Windows
file = sys.argv[1]

# setup arrays
time = []
voltage = []
current = []
diameter = []
state = []

compatibility_mode = False

# open csv
with open(file, newline="") as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        # ignore protocol details
        if row[0][0] != "#" and row[0][0] != "T":
            if not compatibility_mode and len(row) == 3:
                compatibility_mode = True
            time.append(float(row[0]))  # s
            voltage.append(float(row[1]))  # V
            current.append(float(row[2]) * 1e9)  # nA
            if not compatibility_mode:
                diameter.append(float(row[3]))  # nm
                state.append(float(row[4]))  # state


def interpolate_gaps(values):
    """
    Fill gaps using linear interpolation.
    """
    values = np.asarray(values)
    i = np.arange(values.size)
    valid = np.isfinite(values)
    return np.interp(i, i[valid], values[valid])


# data collected without a sustained emitter will have
# (as it should) a lot of NaN values. These will not be
# plotted, leaving a lot of gaps in the data. Instead,
# we perform linear interpolation on the data gaps so
# the plots look clean.
try:
    voltage = interpolate_gaps(voltage)
except:
    pass
try:
    current = interpolate_gaps(current)
except:
    pass
try:
    diameter = interpolate_gaps(diameter)
except:
    pass
try:
    state = interpolate_gaps(state)
except:
    pass

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=time, y=voltage, name="voltage", yaxis="y3", line=dict(color="#bb5566")
    )
)


fig.add_trace(go.Scatter(x=time, y=current, name="current", line=dict(color="#000000")))

if not compatibility_mode:
    fig.add_trace(
        go.Scatter(
            x=time, y=diameter, name="diameter", yaxis="y2", line=dict(color="#004488")
        )
    )

    fig.add_trace(
        go.Scatter(
            x=time, y=state, name="state", yaxis="y4", line=dict(color="#ddaa33")
        )
    )


# Create axis objects
fig.update_layout(
    xaxis=dict(domain=[0.07, 0.95]),
    yaxis=dict(
        title="current (nA)",
        titlefont=dict(color="#000000"),
        tickfont=dict(color="#000000"),
    ),
    yaxis2=dict(
        title="diameter (nm)",
        titlefont=dict(color="#004488"),
        tickfont=dict(color="#004488"),
        anchor="free",
        overlaying="y",
        side="left",
        position=0.00,
    ),
    yaxis3=dict(
        title="voltage (V)",
        titlefont=dict(color="#bb5566"),
        tickfont=dict(color="#bb5566"),
        anchor="x",
        overlaying="y",
        side="right",
    ),
    yaxis4=dict(
        title="state",
        titlefont=dict(color="#ddaa33"),
        tickfont=dict(color="#ddaa33"),
        anchor="free",
        overlaying="y",
        side="right",
        position=1.0,
    ),
)

# Update layout properties
fig.update_layout(
    title_text=os.path.basename(file),
    width=None,
    height=None,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

fig.show()
