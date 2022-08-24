# -*- coding: utf-8 -*-
""" Timer module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

import time

already_running_err = "Timer is already running. Use .stop() to stop it."
not_running_err = "Timer is not running. Use .start() to start it."


class TimerError(Exception):
    """Custom exception to report errors is use of Timer class."""


class Timer:
    def __init__(self):
        self.laps = []

    def __str__(self):
        output = "Lap   Lap times             Overall time"
        for i, t in enumerate(self.laps[1:]):
            output += f"\n{i}     {t-self.laps[i]}    {t-self.laps[0]}"
        return output

    def start(self):
        """Start the timer."""
        if self.running():
            raise TimerError(already_running_err)

        self.laps.append(time.perf_counter())

    def running(self):
        """Return true if the timer is running."""
        return len(self.laps) > 0

    def reset(self):
        """Reset the timer."""
        self.laps = []

    def lap(self):
        """Lap the timer and report lap and total times."""
        if not self.running():
            raise TimerError(not_running_err)
        self.laps.append(time.perf_counter())
        return (self.laps[-1] - self.laps[-2], self.laps[-1] - self.laps[0])

    def start_or_lap(self):
        """Start the timer if it is not running or lap if it is."""
        if self.running():
            self.lap()
        else:
            self.start()

    def lap_if(self, threshold):
        """If the lap time is above the threshold, lap the timer and report the lap and total time."""
        if not self.running():
            raise TimerError(not_running_err)

        cur_time = time.perf_counter()
        if cur_time - self.laps[-1] > threshold:
            self.laps.append(cur_time)
            return (self.laps[-1] - self.laps[-2], self.laps[-1] - self.laps[0], True)

        return (cur_time - self.laps[-1], cur_time - self.laps[0], False)

    def check(self):
        """Check elapsed lap and total time on timer but do not stop."""
        if not self.running():
            raise TimerError(not_running_err)

        cur_time = time.perf_counter()
        return (cur_time - self.laps[-1], cur_time - self.laps[0])
