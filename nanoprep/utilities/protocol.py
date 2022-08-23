# -*- coding: utf-8 -*-
""" Protocol module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""

import os
import inspect
from importlib.machinery import SourceFileLoader


def load_config(path):
    name, ext = os.path.splitext(os.path.basename(path))
    assert ext == ".py", "Configuration should be a .py file"

    mod = SourceFileLoader(name, path).load_module()

    loaded = {}

    for _, item in mod.__dict__.items():
        if inspect.isclass(item):
            if issubclass(item, Protocol):
                loaded[item.name] = item

    assert len(loaded) > 0, "Config must contain at least one protocol"
    return loaded


class Protocol:
    name = "Noop"

    def __init__(self):
        pass

    def __str__(self):
        return self.name

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
        pass
