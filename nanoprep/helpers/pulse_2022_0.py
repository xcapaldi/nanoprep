# -*- coding: utf-8 -*-
""" Pulse module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi
"""

__version__ = "2022.0"
__author__ = "Xavier Capaldi"

import numpy as np


def square_pulse(
    timer,
    sourcemeter,
    emitter,
    aborter,
    pipette_offset,
    pulse_time=0.5,  # s
    pulse_voltage=8,  # V
    state=np.nan,
):
    # ensure timer is started
    timer.start_or_lap()

    sourcemeter.source_voltage = pulse_voltage + pipette_offset

    while True:
        if aborter.should_abort():
            break

        lap_time, total_time = timer.check()

        emitter.record(
            time=total_time,
            voltage=pulse_voltage,
            current=sourcemeter.current,
            state=state,
        )

        if lap_time > pulse_time:
            break


def wait(
    timer, sourcemeter, emitter, aborter, pipette_offset, wait_time=0.5, state=np.nan
):
    square_pulse(
        timer, sourcemeter, emitter, aborter, pipette_offset, wait_time, 0, state
    )
