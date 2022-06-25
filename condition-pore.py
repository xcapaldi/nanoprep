#!/usr/bin/env python3

# Nanopore Conditioning
# AUTHOR: Xavier Capaldi
# DATE: 2022-04-17

# only compatible with Microsoft Windows due to required drivers
# Tested with NI-VISA (v.20.0.0), NI-488.2 (v.19.0.0) on Windows 10

# Install NI-VISA from here:
# https://www.ni.com/en-ca/support/downloads/drivers/download.ni-visa.html#346210

# Install the GPIB-USB driver from here:
# https://knowledge.ni.com/KnowledgeArticleDetails?id=kA03q000000YGw4CAG&l=en-CA

# You will also need PyQt5 installed through pip.

# import necessary packages
import sys
import time
import math
from datetime import datetime
import pyqtgraph as pg
# this is an associated module which should be in the same directory
import poreutils

import logging
log = logging.getLogger('')
log.addHandler(logging.NullHandler())

from pymeasure.log import console_log
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.experiment import Procedure
from pymeasure.experiment import Parameter, IntegerParameter, FloatParameter
from pymeasure.experiment import BooleanParameter, ListParameter
from pymeasure.experiment import Results
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow

# TODO probably I should use pyqtgraph
# import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import numpy as np

# write a new parameter class to hold a text comment string
class StringParameter(Parameter):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    @property
    def value(self):
        if self.is_set():
            return str(self._value)
        else:
            raise ValueError("Parameter value is not set")

    @value.setter
    def value(self, value):
        try:
            value = str(value)
        except ValueError:
            raise ValueError(f"StringParameter given non-string value of "
                             "type {type(value)}")
        self._value = value

    def __str__(self):
        if not self.is_set():
            return ''
        return self._value

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name},value={self._value})>"
    
# TODO apply rounding to all log outputs
class ConditioningProcedure(Procedure):
    # Hardware Settings
    # -------------------------------------------------------------------------
    gpib_address = IntegerParameter('GPIB address',
                                    default=19)
    a_compliance = FloatParameter('Compliance current (A)',
                                  default=1.0)
    # Sample Parameters
    # -------------------------------------------------------------------------
    solution_conductivity = FloatParameter('Solution conductivity (mS/cm)',
                                           default=115.3) # default is 2 M LiCl solution
    effective_length = FloatParameter('Effective pore length (nm)',
                                      default=20)
    channel_conductance = FloatParameter('Channel conductance (S)',
                                          default=0)
    # Protocols
    # -------------------------------------------------------------------------
    protocol = ListParameter('Protocol',
                             choices=["pipette offset",
                                      "holding voltage",
                                      "IV curve",
                                      "big IV curve",
                                      "estimate pore diameter",
                                      "condition/grow",
                                      "grow to dimension",
                                      "square wave condition/grow",
                                      "square wave for time",
                                      "square wave grow to dimension",
                                      "square wave symmetrize"],
                             default="pipette offset")

    progress_style = ListParameter('Progress style',
                                   choices=["absolute percentage",
                                            "relative percentage",
                                            "physical value"],
                                   default="absolute percentage")

    # Protocol Parameters
    # -------------------------------------------------------------------------
    pipette_offset = FloatParameter('Pipette offset (mV)',
                                    default=0)
    hold_time = IntegerParameter('Holding time (s)',
                                 default=5)
    pulse_time = IntegerParameter('Pulse time (ms)',
                                  default=500)
    adaptive_pulse_time = BooleanParameter('Adaptive pulse time',
                                           default=False)
    measurement_voltage = IntegerParameter('Measurement voltage (mV)',
                                           default=400)
    condition_voltage = IntegerParameter('Conditioning/growth voltage (V)',
                                         default=6)
    adaptive_condition_voltage = BooleanParameter('Adaptive conditioning voltage',
                                                  default=False)
    target_diameter = FloatParameter('Target pore diameter (nm)',
                                     default=0)
    target_rectification = FloatParameter('Target rectification ( >1 )',
                                          default=1)
    #check_diameter = BooleanParameter('Check diameter?',
    #                                  default=True)

    # Comment parameter
    comment = StringParameter('Comment')
    
    # order and appearance of columns in data file
    DATA_COLUMNS = ['Time (s)', 'Voltage (V)', 'Current (A)']

    # this function runs first when the procedure is called
    def startup(self):
        log.info(f"Connecting to Keithley 2400 on GPIB::{self.gpib_address}")
        self.sourcemeter = Keithley2400(f"GPIB::{self.gpib_address}")
        log.info("Refresh Keithley 2400")
        self.sourcemeter.reset() # refresh Keithley
        log.info("Enable front terminals")
        self.sourcemeter.use_front_terminals() # enable front and disable rear
        log.info("Configure system to output voltage and measure current")
        self.sourcemeter.measure_current() # setup to measure current
        self.sourcemeter.source_mode = 'voltage' # output voltage mode
        log.info("Set compliance current (max current before system force stop)")
        self.sourcemeter.compliance_current = self.a_compliance # max current before stopping
        log.info("Enable source output and wait for tool to update settings")
        self.sourcemeter.source_enabled = True
        time.sleep(0.1) # wait to give instrument time to react

    # main process in the procedure
    def execute(self):
        # convert units of everything to be consistent
        # TODO this might be a dumb way of doing this
        self.params = {}
        self.params['progress style'] = self.progress_style
        self.params['solution conductivity'] = self.solution_conductivity / 10
        self.params['effective length'] = self.effective_length * (10 ** -9)
        self.params['channel conductance'] = self.channel_conductance
        self.params['pipette offset'] = self.pipette_offset / 1000
        self.params['hold time'] = self.hold_time
        self.params['pulse time'] = self.pulse_time / 1000
        self.params['adaptive time'] = self.adaptive_pulse_time
        self.params['measurement voltage'] = self.measurement_voltage / 1000
        self.params['condition voltage'] = self.condition_voltage
        self.params['adaptive voltage'] = self.adaptive_condition_voltage
        #self.params['target diameter'] = self.target_diameter * (10 ** -9)

        # PIPETTE OFFSET
        # --------------------------------------------------------------------
        if self.protocol == "pipette offset":
            hold_time = 3 # s, note that depending on your capacitances you may want to increase this hold time
            wait_time = 1 # s, depending on capacitances, may want to increase this time as well
            threshold = 0.000000001 # A
            max_offset = 0.250 # V, same as axopatch
            iterations = 15
            
            # run process
            log.info("Begin automated pipette offset")
            log.info("Measure current with no applied voltage")
            # measure 0V baseline
            current_array = []
            t_start = time.perf_counter()
            t_passed = 0
            self.sourcemeter.source_voltage = 0
            while t_passed < hold_time:
                t_passed = time.perf_counter() - t_start

                # depending on capacitances, may want to increase this time as well
                if t_passed > wait_time: 
                    current_array.append(self.sourcemeter.current)

                data = {'Voltage (V)': 0,
                        'Current (A)': self.sourcemeter.current,
                        'Time (s)': t_passed}
                self.emit('results', data) # record data

                # check for process stop
                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    break

            avg_current = np.mean(current_array)
            log.info(f"Baseline at 0V is {avg_current}A")
            
            # check if it is already good enough
            if abs(avg_current) <= threshold:
                log.info("No pipette offset necessary")
                self.emit('progress', 100)
                
            # otherwise use binary search to find offset
            else:
                # set the max offset based on the sign of the average current
                if avg_current > 0:
                    voltage = -max_offset / 2
                else:
                    voltage = max_offset / 2
    
                for i in range(iterations):
                    # measure average current again
                    current_array = []
                    t_start = time.perf_counter()
                    t_passed = 0
                    self.sourcemeter.source_voltage = voltage
                    while t_passed < hold_time:
                        t_passed = time.perf_counter() - t_start

                        if t_passed > wait_time: 
                            current_array.append(self.sourcemeter.current)

                        data = {'Voltage (V)': voltage,
                                'Current (A)': self.sourcemeter.current,
                                'Time (s)': t_passed}
                        self.emit('results', data) # record data

                        # check for process stop
                        if self.should_stop():
                            log.warning("Catch stop command in procedure")
                            break

                    avg_current = np.mean(current_array)
                    log.info(f"Baseline at {voltage}V is {avg_current}A")

                    if avg_current > 0:
                        voltage -= max_offset / (2**(i + 2))
                    else:
                        voltage += max_offset / (2**(i + 2))
                        
                    self.emit('progress', (i+1) * (100/iterations))

                log.info(f"Set pipette offset to {voltage * 1000}mV.")

        # HOLDING VOLTAGE
        # ---------------------------------------------------------------------
        # TODO power spectral density analysis
        if self.protocol == "holding voltage":
            # check there are sensible values
            if self.params['hold time'] <= 0:
                log.error("Hold time must be greater than 0.")
                return
            # run process
            log.info("Begin holding voltage at "
                     f"{self.params['measurement voltage']}V for "
                     f"{self.params['hold time']}s.")
            t_start = time.perf_counter()
            t_passed = 0
            self.sourcemeter.source_voltage = self.params['measurement voltage'] + self.params['pipette offset']
            while t_passed < self.params['hold time']:
                t_passed = time.perf_counter() - t_start
                data = {'Voltage (V)': self.params['measurement voltage'],
                        'Current (A)': self.sourcemeter.current,
                        'Time (s)': t_passed}
                self.emit('results', data) # record data
                self.emit('progress', 100 * t_passed/self.params['hold time'])
                
                # check for process stop
                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    break

        # IV CURVE
        # ---------------------------------------------------------------------
        # TODO add channel conductance subtraction
        elif self.protocol == "IV curve":
            sweep_time = 3 # s
            # arrays are more efficient if instantiated at the desired size
            iv_voltage = [0] * 21
            iv_current = [0] * 21
            log.info("Begin sweeps for IV curve.")
            for i, millivoltage in enumerate(range(-200, 220, 20)):
                t_start = time.perf_counter()
                t_passed = 0
                current_array = []
                self.sourcemeter.source_voltage = millivoltage / 1000 + self.params['pipette offset']
                log.info(f"Begin {millivoltage}mV sweep.")
                while t_passed < sweep_time:
                    t_passed = time.perf_counter() - t_start
                    current = self.sourcemeter.current
                    # record only end of sweep
                    if t_passed > 2 and t_passed <= 3:
                        current_array.append(current)
                    data = {'Voltage (V)': millivoltage / 1000,
                            'Current (A)': current,
                            'Time (s)': t_passed}
                    self.emit('results', data) # record data
                    self.emit('progress',
                              100
                              * (i + (t_passed / sweep_time)) / 21)

                    # check for process stop
                    if self.should_stop():
                        log.warning("Catch stop command in procedure")
                        break
                    
                # after sweep time, save average of end segment to array
                iv_voltage[i] = millivoltage / 1000
                iv_current[i] = np.mean(current_array)

            # after performing all sweeps, can fit the IV values to find G
            def func(v, G, b):
                return G * v + b

            popt, pcov = curve_fit(func, iv_voltage, iv_current)
            log.info(f"Pore conductance is {popt[0]}S.")

            # also estimate the pore diameter
            pore_diameter = poreutils.estimate_diameter(
                solution_conductivity = self.params['solution conductivity'],
                error_conductivity = 0.0001,
                effective_length = self.params['effective length'],
                conductance = popt[0],
                error_conductance = 0.0001,
                channel_conductance =  self.params['channel conductance'],
                error_channel = 0.0001,
                double_electrode = False)[0]
            pore_diameter *= 1E9 # convert to nanometer
            log.info(f"Pore diameter is estimated to be {pore_diameter}nm.")

            # Suggest a pipette offset based on the intersection of the IV plot
            offset = -popt[1]/popt[0] # V
            log.info(f"IV curve is offset from the origin by {offset}V.")
            log.info(f"Consider adjusting pipette offset from prior setting to {(-offset + self.params['pipette offset']) * 1000}mV.")

##            # plot IV curve with fit
##            plt.plot(iv_voltage, iv_current, 'o', label='data')
##            fit_current = [0] * 21
##            for i, voltage in enumerate(iv_voltage):
##                fit_current[i] = func(voltage, popt[0], popt[1])
##            plt.plot(iv_voltage, fit_current, 'r--',
##                     label=f"fit: G={popt[0]}S, b={popt[1]}A")
##            plt.xlabel('voltage (V)')
##            plt.ylabel('current (A)')
##            plt.legend()
##            plt.show()

        # BIG IV
        # ---------------------------------------------------------------------
        # TODO add channel conductance subtraction
        # No fitting implemented here since the pupose of this protocol is
        # purely to see the rectification qualities of the pore.
        elif self.protocol == "big IV curve":
            sweep_time = 3 # s
            # arrays are more efficient if instantiated at the desired size
            iv_voltage = [0] * 81
            iv_current = [0] * 81
            log.info("Begin sweeps for IV curve.")
            for i, millivoltage in enumerate(range(-2000, 2050, 50)):
                t_start = time.perf_counter()
                t_passed = 0
                self.sourcemeter.source_voltage = millivoltage / 1000 + self.params['pipette offset']
                log.info(f"Begin {millivoltage}mV sweep.")
                while t_passed < sweep_time:
                    t_passed = time.perf_counter() - t_start
                    data = {'Voltage (V)': millivoltage / 1000,
                            'Current (A)': self.sourcemeter.current,
                            'Time (s)': t_passed}
                    self.emit('results', data) # record data
                    self.emit('progress',
                              100
                              * (i + (t_passed / sweep_time)) / 81)

                    # check for process stop
                    if self.should_stop():
                        log.warning("Catch stop command in procedure")
                        break
                
        # ESTIMATE PORE DIAMETER
        # ---------------------------------------------------------------------
        elif self.protocol == "estimate pore diameter":
            self.estimate_pore(0, progress = True)
                
        # CONDITION/GROW
        # ---------------------------------------------------------------------
        elif self.protocol == "condition/grow":
            # condition/grow
            pulse_time = self.params['pulse time']
            voltage = self.params['condition voltage']
            t_passed = self.condition_pore(0, pulse_time, voltage)

            # estimate pore diameter
            #self.estimate_pore(t_passed, progress = True)
            
        # GROW TO DIMENSION
        # ---------------------------------------------------------------------
        elif self.protocol == "grow to dimension":
            log.info("Begin automatic pore conditioning/growth with "
                     f"{self.params['condition voltage']}V for "
                     f"{self.params['pulse time']}s.")
            log.info(f"Target diameter is {self.target_diameter}nm.")
            cur_pore, t_passed = self.estimate_pore(0)
            start_pore = cur_pore
            if self.params['progress style'] == "absolute percentage":
                self.emit('progress', 100 * cur_pore / self.target_diameter)
            elif self.params['progress style'] == "relative percentage":
                self.emit('progress', 100 * (cur_pore - start_pore) / (self.target_diameter - start_pore))
            else:
                if cur_pore < 100:
                    self.emit('progress', cur_pore)
                else:
                    self.emit('progress', 100)
            
            while cur_pore < self.target_diameter:
                pulse_time = self.params['pulse time']
                voltage = self.params['condition voltage']
                if self.params['adaptive time']:
                    pulse_time = pulse_time * cur_pore / self.target_diameter
                if self.params['adaptive voltage']:
                    voltage = voltage * cur_pore / self.target_diameter
                t_passed = self.condition_pore(t_passed, pulse_time, voltage)
                cur_pore, t_passed = self.estimate_pore(t_passed)
                if self.params['progress style'] == "absolute percentage":
                    self.emit('progress', 100 * cur_pore / self.target_diameter)
                elif self.params['progress style'] == "relative percentage":
                    self.emit('progress', 100 * (cur_pore - start_pore) / (self.target_diameter - start_pore))
                else:
                    if cur_pore < 100:
                        self.emit('progress', cur_pore)
                    else:
                        self.emit('progress', 100)
                
        # SQUARE WAVE CONDITION/GROW
        # ---------------------------------------------------------------------
        elif self.protocol == "square wave condition/grow":
            # condition/grow
            pulse_time = self.params['pulse time']
            voltage = self.params['condition voltage']
            rect_ratio, t_passed = self.sq_condition_pore(0, pulse_time, voltage)

            # estimate pore diameter
            #self.estimate_pore(t_passed, progress = True)

        # SQUARE WAVE FOR TIME
        # ---------------------------------------------------------------------
        # TODO - make this use helper function
        elif self.protocol == "square wave for time":
            log.info("Begin pore conditioning/growth with "
                     f"{self.params['condition voltage']}V amplitude for "
                     f"{self.params['hold time']}s at "
                     f"{1/self.params['pulse time']}Hz.")

            t_start = time.perf_counter()
            t_passed = 0
            voltage = self.params['condition voltage'] + self.params['pipette offset']

            # condition/grow
            while t_passed < self.params['hold time']:
                t_passed = time.perf_counter() - t_start

                if round(t_passed / self.params['pulse time']) % 2 == 0:
                    self.sourcemeter.source_voltage = -voltage
                    data = {'Voltage (V)': -self.params['condition voltage']}
                else:
                    self.sourcemeter.source_voltage = voltage
                    data = {'Voltage (V)': self.params['condition voltage']}

                data['Current (A)'] = self.sourcemeter.current
                data['Time (s)'] = t_passed

                self.emit('results', data)
                self.emit('progress', 100 * (t_passed / self.params['hold time']))

                # check for pocess stop
                if self.should_stop():
                    log.warning("Catch stop command in procedure")
                    break

            log.info(f"Conditioning procedure finished in {t_passed}s.")

        # SQUARE WAVE GROW TO DIMENSION
        # ---------------------------------------------------------------------
        elif self.protocol == "square wave grow to dimension":
            log.info("Begin automatic pore conditioning/growth with "
                     "a square wave with an amplitude of "
                     f"{self.params['condition voltage']}V and "
                     f"period of {2 * self.params['pulse time']}s.")
            log.info(f"Target diameter is {self.target_diameter}nm.")
            cur_pore, t_passed = self.estimate_pore(0)
            start_pore = cur_pore
            if self.params['progress style'] == "absolute percentage":
                self.emit('progress', 100 * cur_pore / self.target_diameter)
            elif self.params['progress style'] == "relative percentage":
                self.emit('progress', 100 * (cur_pore - start_pore) / (self.target_diameter - start_pore))
            else:
                if cur_pore < 100:
                    self.emit('progress', cur_pore)
                else:
                    self.emit('progress', 100)
            
            while cur_pore < self.target_diameter:
                pulse_time = self.params['pulse time']
                voltage = self.params['condition voltage']
                if self.params['adaptive time']:
                    pulse_time = pulse_time * cur_pore / self.target_diameter
                if self.params['adaptive voltage']:
                    voltage = voltage * cur_pore / self.target_diameter
                rect_ratio, t_passed = self.sq_condition_pore(t_passed, pulse_time, voltage)
                cur_pore, t_passed = self.estimate_pore(t_passed)
                if self.params['progress style'] == "absolute percentage":
                    self.emit('progress', 100 * cur_pore / self.target_diameter)
                elif self.params['progress style'] == "relative percentage":
                    self.emit('progress', 100 * (cur_pore - start_pore) / (self.target_diameter - start_pore))
                else:
                    if cur_pore < 100:
                        self.emit('progress', cur_pore)
                    else:
                        self.emit('progress', 100)

        # SQUARE WAVE SYMMETRIZE
        # ---------------------------------------------------------------------
        elif self.protocol == "square wave symmetrize":
            log.info("Begin automatic pore symmetrization with "
                     "a square wave with an amplitude of "
                     f"{self.params['condition voltage']}V and "
                     f"period of {2 * self.params['pulse time']}s.")
            log.info(f"Target rectification ratio is {self.target_rectification}.")
            log.info(f"Max pore size is {self.target_diameter}nm.")
            cur_pore, t_passed = self.estimate_pore(0)
            start_pore = cur_pore
            rect_ratio = 100

            while (cur_pore < self.target_diameter) and (abs(rect_ratio) > self.target_rectification):
                rect_ratio, t_passed = self.sq_condition_pore(t_passed)
                cur_pore, t_passed = self.estimate_pore(t_passed)
                if rect_ratio < 1:
                    rect_ratio = 1 / rect_ratio
                                
                self.emit('progress', rect_ratio)
                                                 
        # NO PROTOCOL
        # ---------------------------------------------------------------------
        else:
            return

    # ESTIMATE PORE DIAMETER - HELPER FUNCTION
    # -------------------------------------------------------------------------
    def estimate_pore(self, t_prev, progress = False):
        current_array = []
        log.info("Begin pore diameter estimation.")
        t_start = time.perf_counter()
        t_passed = 0
        self.sourcemeter.source_voltage = self.params['measurement voltage'] + self.params['pipette offset']
        while t_passed < self.params['hold time']:
            t_passed = time.perf_counter() - t_start
            current = self.sourcemeter.current
            if t_passed > self.params['hold time'] - 1: # final 1 sec
                current_array.append(current)
            data = {'Voltage (V)': self.params['measurement voltage'],
                    'Current (A)': current,
                    'Time (s)': t_passed + t_prev}
            self.emit('results', data) # record data
            if progress:
                self.emit('progress',
                                  100
                                  * (t_passed / self.params['hold time']))

            # check for process stop
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                break
                
        # after sweep time, estimate pore diameter        
        mean_current = np.mean(current_array)
        log.info(f"Mean current in final second was {mean_current}A.")
        conductance = mean_current / self.params['measurement voltage']
        log.info(f"Conductance is {conductance}S.")
        try:
            pore_diameter = poreutils.estimate_diameter(
                solution_conductivity = self.params['solution conductivity'],
                error_conductivity = 0.0001,
                effective_length = self.params['effective length'],
                conductance = conductance,
                error_conductance = 0.0001,
                channel_conductance = self.params['channel conductance'],
                error_channel = 0.0001,
                double_electrode = False)[0] # arbitrary error added here
            pore_diameter *= 1E9 # convert to nanometer
            log.info(f"Pore diameter is estimated to be {pore_diameter}nm.")
        except:
            pore_diameter = 0.
            log.info(f"Pore diameter cannot be estimated. Either adjust pipette offset or wait until pore is properly wetted.")
        return pore_diameter, t_passed + t_prev # nm, s

    # SQUARE WAVE CONDITION/GROW PORE - HELPER FUNCTION
    # -------------------------------------------------------------------------
    def sq_condition_pore(self, t_prev, pulse_time, voltage):
        log.info("Begin pore conditioning/growth with max"
                 f"{self.params['condition voltage']}V for "
                 f"{self.params['pulse time']}s.")
        t_start = time.perf_counter()
        t_passed = 0

        # lists to store current for rectification calculations
        pos_currents = []
        neg_currents = []
        
        self.sourcemeter.source_voltage = voltage + self.params['pipette offset']
        # condition/grow with positive voltage
        while t_passed < pulse_time:
            t_passed = time.perf_counter() - t_start
            pos_currents.append(self.sourcemeter.current)
            data = {'Voltage (V)': voltage,
                    'Current (A)': pos_currents[-1],
                    'Time (s)': t_prev + t_passed}
            self.emit('results', data) # record data

            # check for process stop
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                break

        # the following is necessary to ensure the positive and negative
        # voltages are applied for the same time
        t_neg_start = time.perf_counter()
        t_neg = 0
        self.sourcemeter.source_voltage = -voltage + self.params['pipette offset']
        # condition/grow with negative voltage
        while t_neg < pulse_time:
            t_neg = time.perf_counter() - t_neg_start
            t_passed = time.perf_counter() - t_start
            neg_currents.append(self.sourcemeter.current)
            data = {'Voltage (V)': -voltage,
                    'Current (A)': neg_currents[-1],
                    'Time (s)': t_prev + t_passed}
            self.emit('results', data) # record data

            # check for process stop
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                break

        rectification_ratio = np.mean(pos_currents) / abs(np.mean(neg_currents))
        log.info(f"Rectification ratio is estimated to be {rectification_ratio}.")
        
        return rectification_ratio, t_passed + t_prev

    # CONDITION/GROW PORE - HELPER FUNCTION
    # -------------------------------------------------------------------------
    def condition_pore(self, t_prev, pulse_time, voltage):
        log.info("Begin pore conditioning/growth with max"
                 f"{self.params['condition voltage']}V for "
                 f"{self.params['pulse time']}s.")
        t_start = time.perf_counter()
        t_passed = 0
        self.sourcemeter.source_voltage = voltage + self.params['pipette offset']
        # condition/grow
        while t_passed < pulse_time:
            t_passed = time.perf_counter() - t_start
            data = {'Voltage (V)': voltage,
                    'Current (A)': self.sourcemeter.current,
                    'Time (s)': t_prev + t_passed}
            self.emit('results', data) # record data

            # check for process stop
            if self.should_stop():
                log.warning("Catch stop command in procedure")
                break

        return t_passed + t_prev

    # safely shut down instrument
    def shutdown(self):
        log.info("Shut down Keithley 2400")
        self.sourcemeter.reset()
        self.sourcemeter.shutdown()

class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=ConditioningProcedure,
            inputs=['gpib_address',
                    'a_compliance',
                    'solution_conductivity',
                    'effective_length',
                    'channel_conductance',
                    'protocol',
                    'progress_style',
                    'pipette_offset',
                    'hold_time',
                    'pulse_time',
                    'adaptive_pulse_time',
                    'measurement_voltage',
                    'condition_voltage',
                    'adaptive_condition_voltage',
                    'target_diameter',
                    'target_rectification',
                    'comment'],
            displays=['gpib_address',
                      'a_compliance',
                      'solution_conductivity',
                      'effective_length',
                      'channel_conductance',
                      'pipette_offset',
                      'protocol',
                      'progress_style',
                      'hold_time',
                      'pulse_time',
                      'adaptive_pulse_time',
                      'measurement_voltage',
                      'condition_voltage',
                      'adaptive_condition_voltage',
                      'target_diameter',
                      'target_rectification',
                      'comment'],
            x_axis='Time (s)',
            y_axis='Current (A)',
            directory_input = True
        )
        self.setWindowTitle('Pore Conditioning/Growth with Keithley 2400')

    def queue(self):
        directory = self.directory
        filename = f"{directory}/{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.csv"
        procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
