# -*- coding: utf-8 -*-
""" IV curve protocol

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

import sys
import time

import numpy as np
from scipy.optimize import curve_fit

sys.path.append("..")
from protocol_template import Protocol
from utilities import calculator, timer


class IVCurve(Protocol):
    """IV curve protocol"""

    def __init__(self):
        super().__init__("iv curve")

    def run(
        self,
        log,
        sourcemeter,
        recorder,
        should_stop,
        solution_conductivity,
        effective_length,
        channel_conductance,
        pipette_offset,
        progressor,
        sweep_start,
        sweep_step,
        sweep_number,
        sweep_duration,
        sweep_discard,
    ):
        """Run IV curve protocol with supplied parameters.

        Args:
            log: Logger.
            sourcemeter: Connected PyMeasure instrument(Keithley2400).
            recorder: Instance of Recorder class with method to emit results.
            should_stop: Function to check if user cancelled procedure.
            solution_conductivity: Solution conductivity in S/m.
            effective_length: The effective length of the nanopore in m (can be approximated for small pores with the membrane thickness.
            channel_conductance: The measured conductance of the channel leading to the pore.
            pipette_offset: An offset to be applied to all raw measurements.
            progressor: Instance of AbsoluteProgressor with method to emit current progress.
            sweep_start: Voltage for first sweep in V.
            sweep_step: Amount to change voltage for each sweep in V.
            sweep_number: Number of sweeps to perform.
            sweep_duration: Time for each sweep.
            sweep_discard: Portion of sweep to discard for analysis (usually to eliminate capacitance) 0-1.
        """
        # validate inputs
        # none required

        # arrays are more efficient if instantiated at the desired size
        iv_voltage = [0] * sweep_number
        iv_current = [0] * sweep_number

        for i, voltage in enumerate(
            np.arange(
                sweep_start, sweep_start + (sweep_step * sweep_number), sweep_step
            )
        ):
            t = timer.Timer()
            t.start()
            current_array = []
            sourcemeter.source_voltage = voltage + pipette_offset
            while t.peak() < sweep_duration:
                current = sourcemeter.current
                # record only end of sweep
                if t.peak_time > sweep_discard and t.peak_time <= sweep_duration:
                    current_array.append(current)

                recorder.record(t.peak_time, voltage, sourcemeter.current)
                progressor.progress(0, sweep_number, i)

                # check for process stop
                if should_stop():
                    log.warning("Catch stop command in procedure")
                    break

            # after sweep time, save average of end segment to array
            iv_voltage[i] = voltage
            iv_current[i] = np.mean(current_array)

            # check for process stop
            if should_stop():
                log.warning("Catch stop command in procedure")
                break

        # after performing all sweeps, can fit the IV values to find G
        def func(v, G, b):
            return G * v + b

        popt, pcov = curve_fit(func, iv_voltage, iv_current)
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

        recorder.record(estimated_diameter=pore_diameter)
        log.info(f"Diameter {pore_diameter * 1E9}nm.")

        # Suggest a pipette offset based on the intersection of the IV plot
        offset = -popt[1] / popt[0]  # V
        log.info(f"Offset {pipette_offset - offset}V.")
