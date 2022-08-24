# -*- coding: utf-8 -*-
""" Nanopore size calculator module

This module is licensed under the MIT License.
Copyright (c) 2022 Xavier Capaldi.

The calculator is based on the paper by Dekker's group:
https://iopscience.iop.org/article/10.1088/0957-4484/22/31/315101/meta
DOI: 10.1088/0957-4484/22/31/315101

also check https://www.solidstatenanopore.com/post/how-to-measure-the-size-of-your-nanopore-electrically
"""

import math


def convert_nm(length):
    """Convert length in nanometers to meters."""

    return length * 10**-9


def convert_mScm(conductivity):
    """Convert conductivity in mS/cm to S/m."""

    return conductivity / 10


def convert_pAmV(conductance):
    """Convert conductance in pA/mV to A/V or S."""

    return conductance * (10**-12) * (1000)


def convert_nAmV(conductance):
    """Convert conductance in nA/mV to A/V or S."""

    return conductance * (10**-9) * (1000)


def estimate_diameter(
    solution_conductivity=11.53,
    error_conductivity=0.0,
    effective_length=2e-08,
    error_length=0.0,
    conductance=0.0,
    error_conductance=0.0,
    channel_conductance=0.0,
    error_channel=0.0,
    double_electrode=False,
):
    """
    Estimate nanopore diameter when pore is open and the surface is
    maximally screened.

    Keyword arguments:
    solution_conductivity -- in units of S/m.
    error_conductivity -- standard error on conductivity measurement.
    effective_length -- effective nanopore length, can estimate as membrane
                        thickness for pores whose diameter is greater than the
                        membrane thickness. Otherwise this will induce
                        significant error. Should be in units of m.
    error_length -- standard error on effective pore length.
    conductance -- in units of A/V or S.
    error_conductance -- standard error on conductance measurement.
    channel_conductance -- port-to-port measurement of conductance.
                           Set to 0 if you have an open pore.
                           In units of A/V or S.
    error_channel -- standard error on channel conductance.
    """

    assert solution_conductivity > 0, "Solution conductivity should be greater than 0."
    assert effective_length > 0, "Effective pore length should be greater than 0."
    assert conductance > 0, "Conductance should be greater than 0."

    # we assume the channel and pore resistances act as resistors in series
    # we also remember that we only need 0.5 * the measured channel resistance
    if channel_conductance > 0:
        if double_electrode:
            branch_conductance = 4 * channel_conductance
            error_branch = error_channel / 4
        else:
            branch_conductance = 2 * channel_conductance
            error_branch = error_channel / 2

        pore_conductance = ((conductance**-1) - (branch_conductance**-1)) ** -1

        # need to calculate error on the isolated pore conductance
        error_pore = (
            pore_conductance
            * (
                math.sqrt(
                    (((error_conductance) / (conductance**2)) ** 2)
                    + (((error_branch) / (branch_conductance**2)) ** 2)
                )
            )
            / ((error_conductance**-1) - (error_branch**-1))
        )
    else:
        pore_conductance = conductance
        error_pore = error_conductance

    K = math.sqrt(
        1
        + (
            (16 * solution_conductivity * effective_length)
            / (math.pi * pore_conductance)
        )
    )

    diameter = (pore_conductance / (2 * solution_conductivity)) * (1 + K)

    error_diameter = math.sqrt(
        (
            (
                ((1 + K) / (2 * solution_conductivity))
                - ((4 * effective_length) / (math.pi * pore_conductance * K))
            )
            ** 2
        )
        * error_pore**2
        + (
            (
                ((4 * effective_length) / (math.pi * solution_conductivity * K))
                - ((pore_conductance / (2 * solution_conductivity**2)) * (1 + K))
            )
            ** 2
        )
        * error_conductivity**2
        + ((4 / (math.pi * K)) ** 2) * error_length**2
    )

    return diameter, error_diameter


def estimate_length(
    solution_conductivity=11.53, dna_diameter=2.2e-9, delta_conductance=0
):
    """
    Run 2kbp or 5kbp dsDNA at 200mV.
    After ~100 translocations, extract the mean from fit to
    distribution of blockage amplitude (single-file events only).
    Only reasonable for small pores where the diameter is less than the
    membrane thickness.

    Keyword arguments:
    solution_conductivity -- in units of S/m.
    dna_diameter -- in units of m. Assume 2.2 nm.
    delta_conductance -- in units of A/V or S.
    """

    assert solution_conductivity > 0, "Solution conductivity should be greater than 0."
    assert dna_diameter > 0, "DNA diameter should be greater than 0 (2.2 nm)."
    assert delta_conductance > 0, "Shift in conductance should be greater than 0."

    effect_length = (solution_conductivity * math.pi * (dna_diameter**2)) / (
        4 * delta_conductance
    )

    return effect_length
