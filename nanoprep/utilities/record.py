# -*- coding: utf-8 -*-
""" Result emitting module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

import numpy as np


class Recorder:
    def __init__(self, emit):
        self.emit = emit

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
            "Estimated diameter (m)": estimated_diameter,
            "State": state,
        }
        self.emit("results", data)
