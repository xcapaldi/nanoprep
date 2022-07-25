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
    defaults = {
        "directory": ".",
        "gpib address": 19,
        "compliance current": 1,
        "solution conductivity": 115.3,
        "effective length": 12,
        "channel conductance": 0,
        "pipette offset": 0,
        "progress style": "absolute",
        "sustained": False,
    }

    for key, item in mod.__dict__.items():
        if inspect.isclass(item):
            if issubclass(item, Protocol):
                loaded[item.name] = item
        if key == "defaults":
            for k, i in item.items():
                defaults[k] = i

    assert len(loaded) > 0, "Config must contain at least one protocol"
    # ensure progress style is one of the accepted options
    if (
        defaults["progress style"] != "absolute"
        and defaults["progress style"] != "relative"
    ):
        defaults["progress style"] = "absolute"
    return loaded, defaults


class Parameters:
    def __init__(
        self,
        sourcemeter,
        log,
        aborter,
        emitter,
        solution_conductivity,
        effective_length,
        channel_conductance,
        pipette_offset,
    ):
        self.sourcemeter = sourcemeter
        self.log = log
        self.aborter = aborter
        self.emitter = emitter
        self.solution_conductivity = solution_conductivity
        self.effective_length = effective_length
        self.channel_conductance = channel_conductance
        self.pipette_offset = pipette_offset


class Protocol:
    name = "Noop"

    def __init__(self):
        pass

    def __str__(self):
        return self.name

    # run accepts a Parameters object
    @staticmethod
    def run(parameters):
        pass
