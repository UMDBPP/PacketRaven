import numpy

# `dh/dt` based on historical flight data
DESCENT_RATE = lambda altitude: -5.8e-08 * altitude ** 2 - 6.001

# integration of `(1/(dh/dt)) dh` based on historical flight data
# TODO make this model better via ML
SECONDS_TO_GROUND = lambda altitude: 1695.02 * numpy.arctan(9.8311e-5 * altitude)
