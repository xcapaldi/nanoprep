# -*- coding: utf-8 -*-
""" Leak Test module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi
"""

__version__ = "2022.0"
__author__ = "Xavier Capaldi"

import numpy as np


def leak_test(
    timer,
    sourcemeter,
    log,
    emitter,
    aborter,
    pipette_offset,  # V
    peak_voltage=1,  # V
    ramp_time=5,
    leak_current=1e-9,  # A
    state=np.nan,
):
    assert ramp_time > 0, "ramp time must be greater than 0"
    # ensure timer is started
    timer.start_or_lap()

    sourcemeter.source_voltage = -peak_voltage + pipette_offset
    peak_current = 0

    while True:
        if aborter.should_abort():
            break

        lap_time, total_time = timer.check()
        voltage = -peak_voltage + (lap_time * (2 * peak_voltage / ramp_time))
        current = sourcemeter.current
        emitter.record(time=total_time, voltage=voltage, current=current, state=state)

        if abs(current) > leak_current and abs(current) > abs(peak_current):
            peak_current = current

        if lap_time > ramp_time:
            break

    if peak_current != 0:
        log.error(f"Leaky: {peak_current}A")
        return True  # i.e. leaky

    return False  # not leaky
