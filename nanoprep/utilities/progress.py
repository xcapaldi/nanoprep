# -*- coding: utf-8 -*-
""" Progress utility module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""


class Progressor:
    def __init__(self, emit):
        self.emit = emit

    def progress(self, initial, target, current):
        pass


class AbsoluteProgressor(Progressor):
    def __init__(self, emit):
        super().__init__(emit)

    def progress(self, initial, target, current):
        self.emit("progress", (100 * (current / target)))


class RelativeProgressor(Progressor):
    def __init__(self, emit):
        super().__init__(emit)

    def progress(self, initial, target, current):
        self.emit("progress", (100 * (current - initial) / (target - initial)))
