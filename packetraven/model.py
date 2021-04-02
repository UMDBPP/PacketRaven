import numpy

# `dh/dt` based on historical flight data
FREEFALL_DESCENT_RATE = lambda altitude: -5.8e-08 * altitude ** 2 - 6.001
# TODO: propagate uncertainty
FREEFALL_DESCENT_RATE_UNCERTAINTY = lambda altitude: 0.2 * FREEFALL_DESCENT_RATE(altitude)

# integration of `(1/(dh/dt)) dh` based on historical flight data
# TODO make this model better with ML
FREEFALL_SECONDS_TO_GROUND = lambda altitude: 1695.02 * numpy.arctan(9.8311e-5 * altitude)
