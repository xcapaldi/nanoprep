# -*- coding: utf-8 -*-
""" Controlled dielectric breakdown module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi
"""

import numpy as np


def flat_cbd(
    timer,
    sourcemeter,
    emitter,
    aborter,
    pipette_offset,
    breakdown_voltage=8,  # V
    cutoff_current=2e-7,  # A
    capacitance_delay=10,  # s
    state=np.nan,
):
    # ensure timer is started
    timer.start_or_lap()

    sourcemeter.source_voltage = breakdown_voltage + pipette_offset

    while True:
        if aborter.should_abort():
            break

        lap_time, total_time = timer.check()
        current = sourcemeter.current

        emitter.record(
            time=total_time, voltage=breakdown_voltage, current=current, state=state
        )

        if lap_time > capacitance_delay:
            if current >= cutoff_current:
                break


def ramp_cbd(
    timer,
    sourcemeter,
    log,
    emitter,
    aborter,
    pipette_offset,
    ramp_start=0,  # V
    ramp_rate=0.1,  # V/s
    cutoff_current=2e-7,  # A
    capacitance_delay=10,  # s
    state=np.nan,
):
    # ensure timer is started
    timer.start_or_lap()

    sourcemeter.source_voltage = ramp_start + pipette_offset

    while True:
        if aborter.should_abort():
            break

        lap_time, total_time = timer.check()
        voltage = ramp_start + (lap_time * ramp_rate)
        sourcemeter.source_voltage = voltage + pipette_offset
        current = sourcemeter.current

        emitter.record(time=total_time, voltage=voltage, current=current, state=state)

        if lap_time > capacitance_delay:
            if current >= cutoff_current:
                break

    log.info(f"Breakdown at {voltage}V")
