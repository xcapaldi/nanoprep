# -*- coding: utf-8 -*-
""" IV Curve module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi
"""

import sys
import numpy as np
from scipy.optimize import curve_fit

sys.path.append("..")
from utilities import calculator


def iv_curve(
    timer,
    sourcemeter,
    log,
    emitter,
    aborter,
    solution_conductivity,
    effective_length,
    channel_conductance,
    pipette_offset,
    sweep_start,
    sweep_step,
    sweep_number,
    sweep_duration,
    sweep_discard,
    stacked,
    estimation_state=np.nan,
    reporting_state=np.nan,
    report_progress=False,
):
    """Run IV curve protocol with supplied parameters.

    Args:
    timer: Instance of Timer class.
    sourcemeter: Connected PyMeasure instrument(Keithley2400).
    log: Logger.
    emitter: Instance of Emitter class with methods to emit results and progress.
    aborter: Instance of Aborter class with methods to check if process should stop.
    solution_conductivity: Solution conductivity in S/m.
    effective_length: The effective length of the nanopore in m (can be approximated for small pores with the membrane thickness.
    channel_conductance: The measured conductance of the channel leading to the pore.
    sweep_start: Voltage for first sweep in V.
    sweep_step: Amount to change voltage for each sweep in V.
    sweep_number: Number of sweeps to perform.
    sweep_duration: Time for each sweep.
    sweep_discard: Portion of sweep to discard for analysis (usually to eliminate capacitance) 0-1.
    stacked: If true, each sweep will occupy the same time and appear stacked otherwise the IV will be stepped.
    estimation_state: The state number that should be recorded when the IV curve is running.
    reporting_state: The state number that should record when reporting the pore size.
    report_progress: Should the progress bar proceed based only on the IV sweeps
    """

    # arrays are more efficient if instantiated at the desired size
    iv_voltage = [0] * sweep_number
    iv_current = [0] * sweep_number

    # make sure the parent timer is started
    if timer.running():
        _, start_time = timer.lap()
    else:
        timer.start()
        start_time = 0

    for i, voltage in enumerate(
        np.arange(sweep_start, sweep_start + (sweep_step * sweep_number), sweep_step)
    ):
        _, t_start = timer.lap()

        if aborter.should_abort():
            break

        current_array = []
        sourcemeter.source_voltage = voltage + pipette_offset

        while True:
            lap_time, total_time = timer.check()
            if lap_time > sweep_duration:
                break
            current = sourcemeter.current

            # record only end of sweep
            if lap_time > sweep_discard and lap_time <= sweep_duration:
                current_array.append(current)

            emitter.record(
                time=start_time + lap_time if stacked else total_time,
                voltage=voltage,
                current=current,
                state=estimation_state,
            )

            if report_progress:
                emitter.progress(0, sweep_number, i)

            # check for process stop
            if aborter.should_abort():
                break

        # after sweep time, save average of end segment to array
        iv_voltage[i] = voltage
        iv_current[i] = np.mean(current_array)

    # check for process stop
    if aborter.should_abort():
        return None

    # after performing all sweeps, can fit the IV values to find G
    def func(v, G, b):
        return G * v + b

    popt, _ = curve_fit(func, iv_voltage, iv_current)
    log.info(f"Conductance = {popt[0]}S.")

    # also estimate the pore diameter
    pore_diameter = calculator.estimate_diameter(
        solution_conductivity=solution_conductivity,
        error_conductivity=0.0001,
        effective_length=effective_length,
        conductance=popt[0],
        error_conductance=0.0001,
        channel_conductance=channel_conductance,
        error_channel=0.0001,
        double_electrode=False,
    )[0]

    emitter.record(
        time=timer.check()[1],
        voltage=voltage,
        current=sourcemeter.current,
        estimated_diameter=pore_diameter * 1e9,
        state=reporting_state,
    )
    log.info(f"Diameter {pore_diameter * 1E9}nm.")

    # Suggest a pipette offset based on the intersection of the IV plot
    offset = -popt[1] / popt[0]  # V
    log.info(f"Offset by {pipette_offset - offset}V.")

    return pore_diameter
