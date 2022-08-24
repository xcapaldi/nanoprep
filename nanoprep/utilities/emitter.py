# -*- coding: utf-8 -*-
""" Emitter module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

import numpy as np


class Emitter:
    def __init__(self, emit, progress_style):
        self.emit = emit
        self.progress_style = progress_style

    def record(
        self,
        time=np.nan,
        voltage=np.nan,
        current=np.nan,
        estimated_diameter=np.nan,
        state=np.nan,
    ):
        data = {
            "Time (s)": time,
            "Voltage (V)": voltage,
            "Current (A)": current,
            "Estimated diameter (nm)": estimated_diameter,
            "State": state,
        }

        self.emit("results", data)

    def progress(self, initial, target, current):
        match self.progress_style:
            case "absolute":
                self.emit("progress", (100 * (current / target)))
            case "relative":
                self.emit("progress", (100 * (current - initial) / (target - initial)))
            case _:
                pass


# SustainedEmitter is a subclass of emitter with one key difference
# If no data is supplied for a data field, instead of emitting np.nan
# the SustainedEmitter emits the last recorded data value.
# The main use for this is for pore size estimation in which there are
# long periods of time with no value emitted.
# Because of this the plotting in the UI is a little broken.
# By using sustained emitter there is always data so the plot should function properly.
# However this should always be used in conjunction with a state value to know when
# you're actually recording a size measurement vs just sustaining the last measurement.
class SustainedEmitter(Emitter):
    def __init__(self, emit, progress_style):
        # these parameters are used for the sustained_record
        self.time = np.nan
        self.voltage = np.nan
        self.current = np.nan
        self.estimated_diameter = np.nan
        self.state = np.nan
        super().__init__(emit, progress_style)

    # sustained_record reports on supplied data. If no data
    # is supplied for a field, the last supplied value is reported.
    # State should be used in conjuction with this to ensure you
    # know when a new measurement is made (for pore size for example).
    # However this ensures the plotting system always works nicely.
    def record(
        self,
        time=np.nan,
        voltage=np.nan,
        current=np.nan,
        estimated_diameter=np.nan,
        state=np.nan,
    ):
        # if a new value is reported, record it internally
        if time is not np.nan:
            self.time = time
        if voltage is not np.nan:
            self.voltage = voltage
        if current is not np.nan:
            self.current = current
        if estimated_diameter is not np.nan:
            self.estimated_diameter = estimated_diameter
        if state is not np.nan:
            self.state = state
        # report data stored internally
        data = {
            "Time (s)": self.time,
            "Voltage (V)": self.voltage,
            "Current (A)": self.current,
            "Estimated diameter (nm)": self.estimated_diameter,
            "State": self.state,
        }

        self.emit("results", data)
