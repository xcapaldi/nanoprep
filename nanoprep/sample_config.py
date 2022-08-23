# -*- coding: utf-8 -*-
""" Sample configuration that is used as the default

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

from utilities.protocol import Protocol
from utilities.timer import Timer
from helpers.iv import iv_curve
from helpers.pulse import square_pulse, wait
from helpers.cbd import flat_cbd, ramp_cbd


class IV(Protocol):
    name = "IV Curve"

    @staticmethod
    def run(
        sourcemeter,
        log,
        aborter,
        emitter,
        solution_conductivity,
        effective_length,
        channel_conductance,
        pipette_offset,
        cutoff_time,
        cutoff_current,
        cutoff_diameter,
    ):
        t = Timer()
        log.info("Start IV Curve protocol")
        iv_curve(
            t,
            sourcemeter,
            log,
            emitter,
            aborter,
            solution_conductivity,
            effective_length,
            channel_conductance,
            pipette_offset,
            -0.2,  # first sweep here
            0.02,  # sweep step
            21,  # number of sweeps
            5,  # sweep duration
            0.75,  # portion of sweep to disregard for pore size estimation
            True,  # stack the sweeps
            report_progress=True,  # progress based on IV only
        )


class SquareWaveGrowToDimension(Protocol):
    name = "Grow to dimension"

    @staticmethod
    def run(
        sourcemeter,
        log,
        aborter,
        emitter,
        solution_conductivity,
        effective_length,
        channel_conductance,
        pipette_offset,
        cutoff_time,
        cutoff_current,
        cutoff_diameter,
    ):
        t = Timer()
        log.info("Start square wave pore growing protocol")
        # take initial IV curve to determine starting size
        init_diameter = iv_curve(
            t,
            sourcemeter,
            log,
            emitter,
            aborter,
            solution_conductivity,
            effective_length,
            channel_conductance,
            pipette_offset,
            -0.2,  # first sweep here
            0.08,  # sweep step
            5,  # number of sweeps
            3,  # sweep duration
            0.75,  # portion of sweep to disregard for pore size estimation
            False,  # do not stack the sweeps
            estimation_state=0,  # state number for running IV
            reporting_state=1,  # state for reporting estimated size
        )

        diameter = init_diameter

        while True:
            if cutoff_diameter is not None:
                if diameter >= cutoff_diameter:
                    break

                emitter.progress(init_diameter, cutoff_diameter, diameter)

            if aborter.should_abort():
                break

            square_pulse(
                t,
                sourcemeter,
                emitter,
                aborter,
                pipette_offset,
                0.5,  # pulse time
                10,  # pulse voltage
                state=2,  # state for pulse application
            )
            diameter = iv_curve(
                t,
                sourcemeter,
                log,
                emitter,
                aborter,
                solution_conductivity,
                effective_length,
                channel_conductance,
                pipette_offset,
                -0.2,  # first sweep here
                0.08,  # sweep step
                5,  # number of sweeps
                3,  # sweep duration
                0.75,  # portion of sweep to disregard for pore size estimation
                False,  # do not stack the sweeps
                estimation_state=0,  # state number for running IV
                reporting_state=1,  # state for reporting estimated size
            )


class CBDRampAndIV(Protocol):
    name = "Ramp CBD and then IV"

    @staticmethod
    def run(
        sourcemeter,
        log,
        aborter,
        emitter,
        solution_conductivity,
        effective_length,
        channel_conductance,
        pipette_offset,
        cutoff_time,
        cutoff_current,
        cutoff_diameter,
    ):
        t = Timer()
        log.info("Start CBD ramp")
        ramp_cbd(
            t,
            sourcemeter,
            log,
            emitter,
            aborter,
            pipette_offset,
            0.0,  # ramp starts at 0V
            0.1,  # ramp at 100mV/s
            2e-7,  # breakdown current
            10,  # 10 second capacitance delay
            state=2,  # breakdown state
        )

        # take IV curve to determine size
        log.info("Start IV Curve protocol")
        iv_curve(
            t,
            sourcemeter,
            log,
            emitter,
            aborter,
            solution_conductivity,
            effective_length,
            channel_conductance,
            pipette_offset,
            -0.2,  # first sweep here
            0.02,  # sweep step
            21,  # number of sweeps
            5,  # sweep duration
            0.75,  # portion of sweep to disregard for pore size estimation
            True,  # stack the sweeps
            report_progress=True,  # progress based on IV only
            estimation_state=0,  # state number for running IV
            reporting_state=1,  # state for reporting estimated size
        )
