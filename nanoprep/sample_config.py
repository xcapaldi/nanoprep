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

# the following variables can be set to change
# the default values appearing in the interface
# not all values have to be set
defaults = {
    "directory": ".",  # default directory for recording data
    "gpib address": 19,
    "compliance current": 1,  # A
    "solution conductivity": 115.3,  # mS/cm - 2 M LiCl
    "effective length": 12,  # nm
    "channel conductance": 0,  # S
    "pipette offset": 0,  # mV
    "progress style": "absolute",
    "cutoff time": 360,  # s
    "cutoff current": 1,  # nA
    "cutoff diameter": 20,  # nm
    "sustained": False,
}


class IV(Protocol):
    name = "IV Curve"

    @staticmethod
    def run(p):
        t = Timer()
        p.log.info("Start IV Curve protocol")
        iv_curve(
            t,
            p.sourcemeter,
            p.log,
            p.emitter,
            p.aborter,
            p.solution_conductivity,
            p.effective_length,
            p.channel_conductance,
            p.pipette_offset,
            sweep_start=-0.2,  # first sweep here
            sweep_step=0.02,  # sweep step
            sweep_number=21,  # number of sweeps
            sweep_duration=5,  # sweep duration
            sweep_discard=0.75,  # portion of sweep to disregard for pore size estimation
            sweep_stacked=True,  # stack the sweeps
            report_progress=True,  # progress based on IV only
        )


class SquareWaveGrowToDimension(Protocol):
    name = "Grow to dimension"

    @staticmethod
    def run(p):
        t = Timer()
        p.log.info("Start square wave pore growing protocol")
        # take initial IV curve to determine starting size
        init_diameter = iv_curve(
            t,
            p.sourcemeter,
            p.log,
            p.emitter,
            p.aborter,
            p.solution_conductivity,
            p.effective_length,
            p.channel_conductance,
            p.pipette_offset,
            sweep_start=-0.2,  # first sweep here
            sweep_step=0.08,  # sweep step
            sweep_number=5,  # number of sweeps
            sweep_duration=3,  # sweep duration
            sweep_discard=0.75,  # portion of sweep to disregard for pore size estimation
            sweep_stacked=False,  # do not stack the sweeps
            estimation_state=0,  # state number for running IV
            reporting_state=1,  # state for reporting estimated size
        )

        diameter = init_diameter

        while True:
            if p.cutoff_diameter is not None:
                if diameter >= p.cutoff_diameter:
                    break

                p.emitter.progress(init_diameter, p.cutoff_diameter, diameter)

            if p.aborter.should_abort():
                break

            square_pulse(
                t,
                p.sourcemeter,
                p.emitter,
                p.aborter,
                p.pipette_offset,
                pulse_time=0.5,  # pulse time
                pulse_voltage=10,  # pulse voltage
                state=2,  # state for pulse application
            )
            diameter = iv_curve(
                t,
                p.sourcemeter,
                p.log,
                p.emitter,
                p.aborter,
                p.solution_conductivity,
                p.effective_length,
                p.channel_conductance,
                p.pipette_offset,
                sweep_start=-0.2,  # first sweep here
                sweep_step=0.08,  # sweep step
                sweep_number=5,  # number of sweeps
                sweep_duration=3,  # sweep duration
                sweep_discard=0.75,  # portion of sweep to disregard for pore size estimation
                sweep_stacked=False,  # do not stack the sweeps
                estimation_state=0,  # state number for running IV
                reporting_state=1,  # state for reporting estimated size
            )


class CBDRampAndIV(Protocol):
    name = "Ramp CBD and then IV"

    @staticmethod
    def run(p):
        t = Timer()
        p.log.info("Start CBD ramp")
        ramp_cbd(
            t,
            p.sourcemeter,
            p.log,
            p.emitter,
            p.aborter,
            p.pipette_offset,
            ramp_start=0.0,
            ramp_rate=0.1,
            cutoff_current=p.cutoff_current * 1e-9
            if p.cutoff_current is not None
            else 200e-9,
            capacitance_delay=10,
            state=1,  # breakdown state
        )

        # wait
        p.log.info("Wait after breakdown")
        wait(
            t,
            p.sourcemeter,
            p.emitter,
            p.aborter,
            p.pipette_offset,
            wait_time=10,  # s
            state=0,  # wait state
        )

        # take IV curve to determine size
        p.log.info("Start IV Curve protocol")
        iv_curve(
            t,
            p.sourcemeter,
            p.log,
            p.emitter,
            p.aborter,
            p.solution_conductivity,
            p.effective_length,
            p.channel_conductance,
            p.pipette_offset,
            sweep_start=-0.2,  # first sweep here
            sweep_step=0.02,  # sweep step
            sweep_number=21,  # number of sweeps
            sweep_duration=5,  # sweep duration
            sweep_discard=0.75,  # portion of sweep to disregard for pore size estimation
            sweep_stacked=False,  # don't stack the sweeps
            estimation_state=2,  # state number for running IV
            reporting_state=3,  # state for reporting estimated size
            report_progress=True,  # progress based on IV only
        )


class CBDRampAndGrowToDimension(Protocol):
    name = "Ramp CBD and Grow To Dimension"

    @staticmethod
    def run(p):
        t = Timer()
        p.log.info("Start CBD ramp")
        ramp_cbd(
            t,
            p.sourcemeter,
            p.log,
            p.emitter,
            p.aborter,
            p.pipette_offset,
            ramp_start=0.0,
            ramp_rate=0.1,
            cutoff_current=p.cutoff_current * 1e-9
            if p.cutoff_current is not None
            else 200e-9,
            capacitance_delay=10,
            state=1,  # breakdown state
        )

        # wait
        p.log.info("Wait after breakdown")
        wait(
            t,
            p.sourcemeter,
            p.emitter,
            p.aborter,
            p.pipette_offset,
            wait_time=10,  # s
            state=0,  # wait state
        )

        # take IV curve to determine size
        p.log.info("Start IV Curve protocol")
        init_diameter = iv_curve(
            t,
            p.sourcemeter,
            p.log,
            p.emitter,
            p.aborter,
            p.solution_conductivity,
            p.effective_length,
            p.channel_conductance,
            p.pipette_offset,
            sweep_start=-0.2,  # first sweep here
            sweep_step=0.02,  # sweep step
            sweep_number=21,  # number of sweeps
            sweep_duration=5,  # sweep duration
            sweep_discard=0.75,  # portion of sweep to disregard for pore size estimation
            sweep_stacked=False,  # stack the sweeps
            estimation_state=2,  # state number for running IV
            reporting_state=3,  # state for reporting estimated size
            report_progress=False,  # progress based on IV only
        )

        diameter = init_diameter

        while True:
            if p.cutoff_diameter is not None:
                if diameter >= p.cutoff_diameter:
                    break

                p.emitter.progress(init_diameter, p.cutoff_diameter, diameter)

            if p.aborter.should_abort():
                break

            square_pulse(
                t,
                p.sourcemeter,
                p.emitter,
                p.aborter,
                p.pipette_offset,
                pulse_time=0.5,  # pulse time
                pulse_voltage=10,  # pulse voltage
                state=4,  # state for pulse application
            )
            diameter = iv_curve(
                t,
                p.sourcemeter,
                p.log,
                p.emitter,
                p.aborter,
                p.solution_conductivity,
                p.effective_length,
                p.channel_conductance,
                p.pipette_offset,
                sweep_start=-0.2,  # first sweep here
                sweep_step=0.08,  # sweep step
                sweep_number=5,  # number of sweeps
                sweep_duration=3,  # sweep duration
                sweep_discard=0.75,  # portion of sweep to disregard for pore size estimation
                sweep_stacked=False,  # do not stack the sweeps
                estimation_state=2,  # state number for running IV
                reporting_state=3,  # state for reporting estimated size
            )
