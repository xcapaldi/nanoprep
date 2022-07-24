# -*- coding: utf-8 -*-
""" Controlled dielectric breakdown

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


class ControlledDielectricBreakdown(Protocol):
    """Controlled dielectric breakdown"""

    def __init__(self):
        super().__init__("controlled dielectric breakdown")

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
        breakdown_voltage,
        cutoff_current,
        capacitance_delay,
    ):
        """Run controlled dielectric breakdown with supplied parameters.

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
            breakdown_voltage: Applied voltage for breakdown.
            cutoff_current: Cutoff current above which the system will shut off voltage application.
            capacitance_delay: Delay before testing the current_cutoff condition to deal with capacitance.
        """
        # validate inputs
        assert breakdown_voltage >= 0, "breakdown voltage must be positive"
        assert cutoff_current >= 0, "cutoff current must be positive"
        assert capacitance_delay >= 0, "capacitance delay must be positive"

        log.info(f"Starting controlled dielectric breakdown")
        t = timer.Timer()
        sourcemeter.source_voltage = breakdown_voltage + pipette_offset
        t.start()

        # first handle capacitance delay
        while t.peak() < capacitance_delay:
            recorder.record(t.peak(), breakdown_voltage, sourcemeter.current)

            # check for process stop
            if should_stop():
                log.warning("Catch stop command in procedure")
                break

        # need initial current
        current = sourcemeter.current

        while current < cutoff_current:
            
            current = sourcemeter.current
            recorder.record(t.peak(), breakdown_voltage, current)

            # check for process stop
            if should_stop():
                log.warning("Catch stop command in procedure")
                break

        progressor.progress(0, 1, 1)
        log.info(f"Finished controlled dielectric breakdown")
