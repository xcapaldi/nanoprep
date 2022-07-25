# -*- coding: utf-8 -*-
""" Pulse module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi
"""

__version__ = "2022.0"
__author__ = "Xavier Capaldi"

import numpy as np


def pipette_offset(
    timer,
    sourcemeter,
    log,
    emitter,
    aborter,
    hold_time=3,  # s
    wait_time=1,  # s
    threshold=1e-9,  # A
    max_offset=0.250,  # V, same as Axopatch
    iterations=15,
    state=np.nan,
):
    # measure 0V baseline
    log.info("Measure current with no applied voltage")
    current_array = []

    # ensure timer is started
    timer.start_or_lap()

    sourcemeter.source_voltage = 0

    while True:
        if aborter.should_abort():
            break

        lap_time, total_time = timer.check()

        if lap_time > wait_time:
            current_array.append(sourcemeter.current)

        emitter.record(
            time=total_time,
            voltage=0,
            current=sourcemeter.current,
            state=state,
        )

        if lap_time > hold_time:
            break

    if aborter.should_abort():
        return 0

    avg_current = np.mean(current_array)
    log.info(f"Baseline at 0V is {avg_current}A")

    # check if it is already good enough
    if abs(avg_current) <= threshold:
        log.info("No pipette offset necessary")
        return 0

    # otherwise use binary search to find offset
    if avg_current > 0:
        voltage = -max_offset / 2
    else:
        voltage = max_offset / 2

    for i in range(iterations):
        if aborter.should_abort():
            break

        # measure average current again
        current_array = []
        timer.lap()
        sourcemeter.source_voltage = voltage

        while True:
            if aborter.should_abort():
                break

            lap_time, total_time = timer.check()

            if lap_time > wait_time:
                current_array.append(sourcemeter.current)

            emitter.record(
                time=total_time,
                voltage=0,
                current=sourcemeter.current,
                state=state,
            )

            if lap_time > hold_time:
                break

        avg_current = np.mean(current_array)
        log.info(f"Baseline at {voltage}V is {avg_current}A")
        emitter.progress(0, iterations, i)

        if abs(avg_current) <= threshold:
            log.info(f"Pipette offset: {voltage * 1000}mV.")
            return voltage

        if avg_current > 0:
            voltage -= max_offset / (2 ** (i + 2))
        else:
            voltage += max_offset / (2 ** (i + 2))

    log.info(f"Pipette offset: {voltage * 1000}mV.")
    return voltage
