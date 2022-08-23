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
