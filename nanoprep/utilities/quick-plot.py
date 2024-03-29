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
import matplotlib.pyplot as plt

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

num_plots = 2
if compatibility_mode:
    num_plots = 1

plt.style.use("tableau-colorblind10")
plt.tight_layout()

# plot current
ax1 = plt.subplot(num_plots, 1, num_plots)
(current_plot,) = plt.plot(time, current, linestyle="-", color="C0", label="Current")
plt.tick_params("x", labelbottom=False)
plt.ylabel("current (nA)")

# plot voltage
# ax2 = plt.subplot(num_plots,1,num_plots-1, sharex=ax1)
ax2 = ax1.twinx()
(voltage_plot,) = plt.plot(time, voltage, linestyle="--", color="C2", label="Voltage")
plt.xlabel("time (s)")
plt.ylabel("voltage (V)")
plt.legend(handles=[voltage_plot, current_plot])
if compatibility_mode:
    plt.title(os.path.basename(file))

if not compatibility_mode:
    # plot state
    ax3 = plt.subplot(num_plots, 1, num_plots - 1, sharex=ax1)
    (state_plot,) = plt.plot(time, state, linestyle="-", color="C3", label="State")
    plt.tick_params("x", labelbottom=False)
    plt.ylabel("state")

    # plot estimated diameter
    # ax4 = plt.subplot(num_plots,1,num_plots-3, sharex=ax1)
    ax4 = ax3.twinx()
    (diameter_plot,) = plt.plot(
        time, diameter, linestyle="--", color="C1", label="Diameter"
    )
    plt.tick_params("x", labelbottom=False)
    plt.ylabel("diameter (nm)")
    plt.title(os.path.basename(file))
    plt.legend(handles=[diameter_plot, state_plot])

plt.show()
