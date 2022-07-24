# -*- coding: utf-8 -*-
""" Config-loading utility module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.
"""


def from_config(config, protocol, parameter, default):
    if protocol in config:
        return type(default)(config[protocol].get(parameter, str(default)))
    return default
