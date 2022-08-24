# -*- coding: utf-8 -*-
""" Aborter module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""


class Aborter:
    def __init__(self, should_stop, log):
        self.should_stop = should_stop
        self.log = log

    def should_abort(self, log_message="Catch stop command in procedure"):
        if self.should_stop():
            self.log.warning(log_message)
            return True

        return False
