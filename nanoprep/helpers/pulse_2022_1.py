# -*- coding: utf-8 -*-
""" Pulse module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi
"""

__version__ = "2022.1"
__author__ = "Xavier Capaldi"

import numpy as np


def wait(
    timer, sourcemeter, emitter, aborter, pipette_offset, wait_time=0.5, state=np.nan
):
    square_pulse(
        timer, sourcemeter, emitter, aborter, pipette_offset, wait_time, 0, state
    )


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


def adaptive_amplitude_square_pulse(
    timer,
    sourcemeter,
    emitter,
    aborter,
    pipette_offset,
    # pore size progress
    initial_size,
    current_size,
    target_size,
    # pulse max parameters
    pulse_time=0.5,  # s
    pulse_voltage=8,  # V
    min_voltage=3,  # V
    state=np.nan,
):
    # ensure timer is started
    timer.start_or_lap()

    # voltage is inversely proportional to progress
    # if the voltage would be lower than the minimum voltage, use
    # that instead
    assert (
        target_size > initial_size
    ), "target pore size must be larger than the initial size"
    progress = (current_size - initial_size) / (target_size - initial_size)
    adaptive_voltage = (1 - progress) * (pulse_voltage + pipette_offset)
    if abs(adaptive_voltage) < abs(min_voltage):
        sourcemeter.source_voltage = min_voltage
    else:
        sourcemeter.source_voltage = adaptive_voltage

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


def adaptive_period_square_pulse(
    timer,
    sourcemeter,
    emitter,
    aborter,
    pipette_offset,
    # pore size progress
    initial_size,
    current_size,
    target_size,
    # pulse max parameters
    pulse_time=0.5,  # s
    min_time=0.2,  # s
    pulse_voltage=8,  # V
    state=np.nan,
):
    # ensure timer is started
    timer.start_or_lap()

    # pulse time is inversely proportional to progress
    # if the time would be lower than the minimum time, use
    # that instead
    progress = current_size / (target_size - initial_size)
    adaptive_time = (1 - progress) * pulse_time
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

        if lap_time > adaptive_time and lap_time > min_time:
            break


def adaptive_square_pulse(
    timer,
    sourcemeter,
    emitter,
    aborter,
    pipette_offset,
    # pore size progress
    initial_size,
    current_size,
    target_size,
    # pulse max parameters
    pulse_time=0.5,  # s
    min_time=0.2,  # s
    pulse_voltage=8,  # V
    min_voltage=3,  # V
    state=np.nan,
):
    # ensure timer is started
    timer.start_or_lap()

    # voltage and time are inversely proportional to progress
    # if either would be lower than the set minimum, use
    # that instead
    progress = (current_size - initial_size) / (target_size - initial_size)
    adaptive_time = (1 - progress) * pulse_time
    adaptive_voltage = (1 - progress) * (pulse_voltage + pipette_offset)
    if abs(adaptive_voltage) < abs(min_voltage):
        sourcemeter.source_voltage = min_voltage
    else:
        sourcemeter.source_voltage = adaptive_voltage

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

        if lap_time > adaptive_time and lap_time > min_time:
            break
