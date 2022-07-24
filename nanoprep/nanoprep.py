# -*- coding: utf-8 -*-
""" NanoPrep

MIT License

Copyright (c) 2022 Xavier Capaldi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

only compatible with Microsoft Windows due to required drivers
Tested with NI-VISA (v.20.0.0), NI-488.2 (v.19.0.0) on Windows 10

Install NI-VISA from here:
https://www.ni.com/en-ca/support/downloads/drivers/download.ni-visa.html#346210

Install the GPIB-USB driver from here:
https://knowledge.ni.com/KnowledgeArticleDetails?id=kA03q000000YGw4CAG&l=en-CA
"""

import sys
import time
import math
import logging
import configparser
from datetime import datetime
from pathlib import Path

from pymeasure.log import console_log
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.experiment import Procedure
from pymeasure.experiment import Parameter, IntegerParameter, FloatParameter
from pymeasure.experiment import BooleanParameter, ListParameter
from pymeasure.experiment import Results
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow

from utilities import maybe, progress, record
import protocols

iv_curve = protocols.IVCurve()
controlled_dielectric_breakdown = protocols.ControlledDielectricBreakdown()

log = logging.getLogger("")
log.addHandler(logging.NullHandler())

# inputs stored as global variable so we can modify from within the Procedure
inputs = [
    "gpib_address",
    "compliance_current",
    "solution_conductivity",
    "effective_length",
    "channel_conductance",
    "pipette_offset",
    "progress_style",
    "protocol",
]

# read user configuration if supplied by dropping
# onto this script in windows
config = configparser.ConfigParser()
if len(sys.argv) > 1:
    config.read(sys.argv[1])
if len(config.sections()) == 0:
    config.read("default.ini")


class NanoprepProcedure(Procedure):
    # order and appearance of columns in data file
    DATA_COLUMNS = [
        "Time (s)",
        "Voltage (V)",
        "Current (A)",
        "Estimated diameter (m)",
        "State",
    ]

    # Hardware Settings
    gpib_address = IntegerParameter(
        "GPIB address", default=maybe.from_config(config, "DEFAULT", "gpib address", 19)
    )
    compliance_current = FloatParameter(
        "Compliance current",
        units="A",
        default=maybe.from_config(config, "DEFAULT", "compliance current", 1.0),
        minimum=0,
    )

    # Sample Parameters
    solution_conductivity = FloatParameter(
        "Solution conductivity",
        units="S/m",
        # default is 2 M LiCl
        default=maybe.from_config(config, "DEFAULT", "solution conductivity", 11.53),
        minimum=0,
    )
    effective_length = FloatParameter(
        "Effective pore length",
        units="m",
        default=maybe.from_config(config, "DEFAULT", "effective pore length", 20e-9),
        minimum=0,
    )
    channel_conductance = FloatParameter(
        "Channel conductance",
        units="S",
        default=maybe.from_config(config, "DEFAULT", "channel conductance", 0.0),
        minimum=0,
    )

    # Experiment Parameters
    pipette_offset = FloatParameter(
        "Pipette offset",
        units="V",
        default=maybe.from_config(config, "DEFAULT", "pipette offset", 0.0),
    )

    progress_style = ListParameter(
        "Progress style",
        choices=["absolute", "relative"],
        default=maybe.from_config(config, "DEFAULT", "progress style", "absolute"),
    )

    # Protocols
    protocol = ListParameter(
        "Protocol", choices=config.sections(), default=config.sections()[0]
    )

    # Protocol specific parameters
    ## iv curve
    iv_curve_sweep_start = FloatParameter(
        "First sweep",
        units="V",
        default=maybe.from_config(config, iv_curve.name, "sweep start", -0.2),
        group_by=f"{protocol=}".split("=")[0],
        group_condition=iv_curve.name,
    )
    iv_curve_sweep_step = FloatParameter(
        "Step between sweeps",
        units="V",
        default=maybe.from_config(config, iv_curve.name, "sweep step", 0.02),
        group_by=f"{protocol=}".split("=")[0],
        group_condition=iv_curve.name,
    )
    iv_curve_sweep_number = IntegerParameter(
        "Number of sweeps",
        default=maybe.from_config(config, iv_curve.name, "sweep number", 21),
        minimum=1,
        group_by=f"{protocol=}".split("=")[0],
        group_condition=iv_curve.name,
    )
    iv_curve_sweep_duration = FloatParameter(
        "Sweep duration",
        units="s",
        default=maybe.from_config(config, iv_curve.name, "sweep duration", 3),
        minimum=0,
        group_by=f"{protocol=}".split("=")[0],
        group_condition=iv_curve.name,
    )
    iv_curve_sweep_discard = FloatParameter(
        "Initial portion of sweep to discard in analyis",
        units="s",
        default=maybe.from_config(config, iv_curve.name, "sweep discard", 2),
        minimum=0,
        group_by=f"{protocol=}".split("=")[0],
        group_condition=iv_curve.name,
    )
    inputs.extend(
        [
            f"{iv_curve_sweep_start=}".split("=")[0],
            f"{iv_curve_sweep_step=}".split("=")[0],
            f"{iv_curve_sweep_number=}".split("=")[0],
            f"{iv_curve_sweep_duration=}".split("=")[0],
            f"{iv_curve_sweep_discard=}".split("=")[0],
        ]
    )

    ## controlled dielectric breakdown
    controlled_dielectric_breakdown_breakdown_voltage = FloatParameter(
        "Breakdown voltage",
        units="V",
        default=maybe.from_config(
            config, controlled_dielectric_breakdown.name, "breakdown voltage", 8
        ),
        minimum=0,
        group_by=f"{protocol=}".split("=")[0],
        group_condition=controlled_dielectric_breakdown.name,
    )
    controlled_dielectric_breakdown_cutoff_current = FloatParameter(
        "Cutoff current",
        units="A",
        default=maybe.from_config(
            config, controlled_dielectric_breakdown.name, "cutoff current", 200e-9
        ),
        minimum=0,
        group_by=f"{protocol=}".split("=")[0],
        group_condition=controlled_dielectric_breakdown.name,
    )
    controlled_dielectric_breakdown_capacitance_delay = FloatParameter(
        "Capacitance delay",
        units="s",
        default=maybe.from_config(
            config, controlled_dielectric_breakdown.name, "capacitance delay", 20
        ),
        minimum=0,
        group_by=f"{protocol=}".split("=")[0],
        group_condition=controlled_dielectric_breakdown.name,
    )
    inputs.extend(
        [
            f"{controlled_dielectric_breakdown_breakdown_voltage=}".split("=")[0],
            f"{controlled_dielectric_breakdown_cutoff_current=}".split("=")[0],
            f"{controlled_dielectric_breakdown_capacitance_delay=}".split("=")[0],
        ]
    )

    # this function runs first when the procedure is called
    def startup(self):
        log.info(f"Connecting to Keithley 2400 on GPIB::{self.gpib_address}")
        self.sourcemeter = Keithley2400(f"GPIB::{self.gpib_address}")
        log.info("Refresh Keithley 2400")
        self.sourcemeter.reset()  # refresh Keithley
        log.info("Enable front terminals")
        self.sourcemeter.use_front_terminals()  # enable front and disable rear
        log.info("Configure system to output voltage and measure current")
        self.sourcemeter.measure_current()  # setup to measure current
        self.sourcemeter.source_mode = "voltage"  # output voltage mode
        log.info("Set compliance current (max current before system force stop)")
        self.sourcemeter.compliance_current = (
            self.compliance_current
        )  # max current before stopping
        log.info("Enable source output and wait for tool to update settings")
        self.sourcemeter.source_enabled = True
        time.sleep(0.1)  # wait to give instrument time to react

    # main process in the procedure
    def execute(self):
        recorder = record.Recorder(self.emit)
        match self.progress_style:
            case "absolute":
                progressor = progress.AbsoluteProgressor(self.emit)
            case "relative":
                progressor = progress.RelativeProgressor(self.emit)
            case _:
                pass

        match self.protocol:
            case iv_curve.name:
                iv_curve.run(
                    log,
                    self.sourcemeter,
                    recorder,
                    self.should_stop,
                    self.solution_conductivity,
                    self.effective_length,
                    self.channel_conductance,
                    self.pipette_offset,
                    progress.AbsoluteProgressor(self.emit),
                    self.iv_curve_sweep_start,
                    self.iv_curve_sweep_step,
                    self.iv_curve_sweep_number,
                    self.iv_curve_sweep_duration,
                    self.iv_curve_sweep_discard,
                )
            case controlled_dielectric_breakdown.name:
                controlled_dielectric_breakdown.run(
                    log,
                    self.sourcemeter,
                    recorder,
                    self.should_stop,
                    self.solution_conductivity,
                    self.effective_length,
                    self.channel_conductance,
                    self.pipette_offset,
                    progress.AbsoluteProgressor(self.emit),
                    self.controlled_dielectric_breakdown_breakdown_voltage,
                    self.controlled_dielectric_breakdown_cutoff_current,
                    self.controlled_dielectric_breakdown_capacitance_delay,
                )
            case _:
                pass

    # safely shut down instrument
    def shutdown(self):
        log.info("Shut down Keithley 2400")
        self.sourcemeter.reset()
        self.sourcemeter.shutdown()


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=NanoprepProcedure,
            inputs=inputs,
            # this actually goes into the display window at bottom
            displays=[
                "solution_conductivity",
                "effective_length",
                "channel_conductance",
                "pipette_offset",
                "protocol",
            ],
            x_axis="Time (s)",
            y_axis="Current (A)",
            inputs_in_scrollarea=True,
            hide_groups=True,
            directory_input=True,
        )
        self.directory = maybe.from_config(config, "DEFAULT", "data directory", ".")
        self.setWindowTitle(
            "Nanoprep: pore formation, characterization, growth and conditioning"
        )

    def queue(self):
        directory = self.directory
        filename = f"{directory}/{datetime.now().strftime('%Y%m%dT%H%M%S')}.csv"
        procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
