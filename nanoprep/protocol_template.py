# -*- coding: utf-8 -*-
""" Protocol class

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
"""


class Protocol:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def run(
        self,
        sourcemeter,
        log,
        emit,
        should_stop,
        solution_conductivity,
        effective_length,
        channel_conductance,
        pipette_offset,
        progressor,
    ):
        """Run protocol.

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
        """
        pass
