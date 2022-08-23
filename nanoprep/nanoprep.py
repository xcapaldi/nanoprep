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
import logging
from datetime import datetime

from pymeasure.log import console_log
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.experiment import Procedure
from pymeasure.experiment import Parameter, IntegerParameter, FloatParameter
from pymeasure.experiment import BooleanParameter, ListParameter
from pymeasure.experiment import Results
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow

from utilities.aborter import Aborter
from utilities.emitter import Emitter
from utilities.protocol import load_config


log = logging.getLogger("")
log.addHandler(logging.NullHandler())

# read user configuration if supplied by dropping
# onto this script in windows
if len(sys.argv) > 1:
    config = sys.argv[1]
else:
    config = "sample_config.py"

loaded = load_config(config)


class NanoprepProcedure(Procedure):
    # order and appearance of columns in data file
    DATA_COLUMNS = [
        "Time (s)",
        "Voltage (V)",
        "Current (A)",
        "Estimated diameter (nm)",
        "State",
    ]

    # Hardware Settings
    gpib_address = IntegerParameter(
        "GPIB address",
        default=19,
    )
    compliance_current = FloatParameter(
        "Compliance current",
        units="A",
        default=1.0,
        minimum=0,
    )

    # Sample Parameters
    solution_conductivity = FloatParameter(
        "Solution conductivity",
        units="mS/cm",
        # default is 2 M LiCl
        default=115.3,
        minimum=0,
    )
    effective_length = FloatParameter(
        "Effective pore length",
        units="nm",
        default=12,
        minimum=0,
    )
    channel_conductance = FloatParameter(
        "Channel conductance",
        units="S",
        default=0,
        minimum=0,
    )

    # Experiment Parameters
    pipette_offset = FloatParameter(
        "Pipette offset",
        units="mV",
        default=0,
    )

    progress_style = ListParameter(
        "Progress style",
        choices=["absolute", "relative"],
        default="absolute",
    )

    # Protocols
    protocol = ListParameter(
        "Protocol", choices=list(loaded.keys()), default=list(loaded.keys())[0]
    )

    # Cutoffs
    enable_cutoff_time = BooleanParameter("Cutoff time", default=False)
    cutoff_time = FloatParameter(
        "Cutoff time",
        units="s",
        default=360,
        minimum=0,
        group_by="enable_cutoff_time",
    )

    enable_cutoff_current = BooleanParameter("Cutoff current", default=False)
    cutoff_current = FloatParameter(
        "Cutoff current",
        units="nA",
        default=1,
        minimum=0,
        group_by="enable_cutoff_current",
    )

    enable_cutoff_diameter = BooleanParameter("Cutoff pore diameter", default=False)
    cutoff_diameter = FloatParameter(
        "Cutoff pore diameter",
        units="nm",
        default=20,
        minimum=0,
        group_by="enable_cutoff_diameter",
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
        # refresh the configuration to get latest parameter changes
        load_config(config)[self.protocol].run(
            self.sourcemeter,
            log,
            Aborter(self.should_stop, log),
            Emitter(self.emit, self.progress_style),
            self.solution_conductivity / 10,  # S/m
            self.effective_length * 10**-9,  # m
            self.channel_conductance,
            self.pipette_offset / 1000,  # V
            self.cutoff_time if self.enable_cutoff_time else None,
            self.cutoff_current * 10**-9 if self.enable_cutoff_current else None,
            self.cutoff_diameter * 10**-9 if self.enable_cutoff_diameter else None,
        )

    # safely shut down instrument
    def shutdown(self):
        log.info("Shut down Keithley 2400")
        self.sourcemeter.reset()
        self.sourcemeter.shutdown()


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=NanoprepProcedure,
            inputs=[
                "gpib_address",
                "compliance_current",
                "solution_conductivity",
                "effective_length",
                "channel_conductance",
                "pipette_offset",
                "progress_style",
                "protocol",
                "enable_cutoff_time",
                "cutoff_time",
                "enable_cutoff_current",
                "cutoff_current",
                "enable_cutoff_diameter",
                "cutoff_diameter",
            ],
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
        self.directory = "."
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
