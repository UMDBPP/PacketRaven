
"""
/* Link Telemetry v2.0 "Mobile"

   Copyright (c) 2015-2017 University of Maryland Space Systems Lab
   NearSpace Balloon Payload Program

   Written by Nicholas Rossomando
   2015-04-11

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:

   The above copyright notice and this permission notice shall be included in all
   copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
   SOFTWARE.

   GroundTrack.py:

   Defines ground track functions. Does heavy lifting of calculation and handling
   separate ground tracks.
*/
"""

import time
import pyserial
import PacketClass
import LogClass


class GroundTrack:

    """
    Sets up the GroundTrack class with all vars and initial conditions.
    """

    def __init__(self, cap, jfile, kfile):
        self.capturedPackets = cap  # Number of packets we've collected and kept so far.
        self.logEnabled = False  # Whether we're logging captured data or not. Default False
        self.jsonEnabled = False  # Same as above but for JSON log.
        self.kmlEnabled = False  # And same as above but for KML log.
        self.jsonFilename = jfile  # Filename for JSON log
        self.kmlFilename = kfile  # Filename for KML log
        self.ascentRate = 0  # ft/sec, default 0
        self.groundSpeed = 0  # mph, default 0
        self.downrangeDist = 0  # mi, default 0
        self.timeToImpact = -5  # sec, default -5
        self.latlonDerrivative = [0, 0]  # Rate of change of lat and lon. Lat index 0, lon index 1. Default 0
        self.latestCallsign = [['', '', ''], []]  # Stores latest callsigns of packets. Only need 2, 3 for safety.
        # Index 0 = most recent. Default empty

    def calculateAscentRate(self):
        """
        Calculate ascent rate function.
        Simple difference right now.
        Will look into filtering very, very soon.
        (Need to make it work before I make it better.)
        Emits result in ft/s; conversion to m/s in print function.
        If ascent rate is negative (descent rate), also estimate time to sea level impact.
        """

        calcPackets = getLatest(2)  # Gets the 2 most recent packets
        deltaAltitude = calcPackets[0].getPacket().alt - calcPackets[1].getPackets().alt  # Calc diff in alt in ft
        deltaTime = diffTime(calcPackets)  # Get time between packets

        if deltaTime != 0:
            ascentRate = deltaAltitude/deltaTime

    def calculateAscentRate(self):
        """
        Ground speed calculation function.
        Simple difference - won't be filtered.
        Filter here would change GPS provided coords,
        And I honestly don't want to do that.
        This isn't really that critical anyway.
        Emits result in mph; conversion to m/s in print function.
        """

        calcPackets = getLatest(2)  # Gets the 2 most recent packets
        distanceTraveled = diffLatLon(calcPackets)  # Get ground distance between packets
        deltaTime = diffTime(calcPackets)  # Get time between packets

        if deltaTime != 0:
            hours = deltaTime/3600  # Converts from seconds to hours
            groundSpeed = distanceTraveled/hours  # Calc speed in MPH



