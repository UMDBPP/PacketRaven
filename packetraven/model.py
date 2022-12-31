"""
this module defines models and approximations useful for predicting flight behavior
"""

import numpy


# `dh/dt` based on historical flight data
def FREEFALL_DESCENT_RATE(altitude):
    return -5.8e-08 * altitude**2 - 6.001


# TODO: propagate uncertainty
def FREEFALL_DESCENT_RATE_UNCERTAINTY(altitude):
    return 0.2 * FREEFALL_DESCENT_RATE(altitude)


# integration of `(1/(dh/dt)) dh` based on historical flight data
# TODO make this model better with ML
def FREEFALL_SECONDS_TO_GROUND(altitude):
    return 1695.02 * numpy.arctan(9.8311e-05 * altitude)
