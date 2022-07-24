# -*- coding: utf-8 -*-
""" Timer module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

import time


class TimerError(Exception):
    """Custom exception to report errors is use of Timer class."""


class Timer:
    def __init__(self):
        self.start_time = None
        self.peak_time = None

    def start(self):
        """Start a new timer."""
        if self.start_time is not None:
            raise TimerError(f"Timer is running. Use .stop() to stop it.")

        self.start_time = time.perf_counter()

    def stop(self):
        """Stop the timer and report the elapsed time."""
        if self.start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it.")

        elapsed_time = time.perf_counter() - self.start_time
        self.start_time = None
        return elapsed_time

    def peak(self):
        """Check and store elapsed time on timer but do not stop."""
        if self.start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it.")

        self.peak_time = time.perf_counter() - self.start_time
        return self.peak_time
