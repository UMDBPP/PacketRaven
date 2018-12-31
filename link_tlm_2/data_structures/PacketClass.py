
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

   PacketClass.py:

   Raw packet parsing and error checking class.
    Uses DecodedPacket as its data structure.
*/
"""

from link_tlm_2.output import Parser

class Packet:

    def __init__(self, cs, ts, _lat, _lon, _alt, _heading, _speed, cmt):
        self.callsign = cs
        self.timestamp = ts
        self.lat = _lat
        self.lon = _lon
        self.alt = _alt
        self.heading = _heading
        self.speed = _speed
        self.comment = cmt
        self.validPacket = True

    def validityCheck(self, parsedPacket):
        if parsedPacket.callsign == '' or parsedPacket.timestamp == '' or parsedPacket.lat == 1000.0 or parsedPacket.lon == 1000.0:
            self.validPacket = False

        if parsedPacket.callsign == 'None' or parsedPacket.alt == -100000:
            self.validPacket = False

    def parse(self, rawPacket):
        parsedPacket = self.newPacket()  # Creates a packet with the default values
        parsedPacket.callsign = Parser.getCallsign(rawPacket)  # Gets packet callsign
        parsedPacket.timestamp = Parser.getTimestamp(rawPacket)  # Gets timestamp
        parsedPacket.alt = Parser.getAlt(rawPacket)  # Gets Alt
        parsedPacket.heading = Parser.getCse(rawPacket)  # Gets course
        parsedPacket.speed = Parser.getSpd(rawPacket)  # Gets Speed
        parsedPacket.comment = Parser.getCmt(rawPacket)  # Gets comment

        uglyLat = Parser.getLat(rawPacket)  # Gets latitude
        if uglyLat == 'None':  # Validity check
            parsedPacket.validPacket = False

        if len(uglyLat) == 8:  # Uncompressed
            deg = float(uglyLat[0:2])
            mins = float(uglyLat[2:5])
            direction = uglyLat[7]

            parsedPacket. lat = deg + (mins/60)  # Convert from DMS to decimal
            if direction == 'S':
                parsedPacket.lat = -parsedPacket.lat

        else:  # Compressed
            parsedPacket.lat = Parser.decompressLat(uglyLat)  # No conversions needed here.

        uglyLon = Parser.getLon(rawPacket)  # Gets longitude
        if uglyLon == 'None':  # Validity check
            parsedPacket.validPacket = False

        if len(uglyLon):  # Uncompressed
            deg = float(uglyLon[0:2])
            mins = float(uglyLon[2:5])
            direction = uglyLon[8]

            parsedPacket.lon = deg + (mins/60)   # Convert from DMS to decimal
            if direction == 'W':
                parsedPacket.lon = -parsedPacket.lon

        else:  # Compressed
            parsedPacket.lon = Parser.decompressLon(uglyLon)  # No conversions needed here.

        self.validityCheck(parsedPacket)

    def prnt(self, parsedPacket):
        print 'Callsign: ', parsedPacket.callsign, '\n'
        print 'Time: ', parsedPacket.timestamp, '\n'
        print 'Lat: ', parsedPacket.lat, '\n'
        print 'Lon: ', parsedPacket.lon, '\n'
        print 'Alt (ft): ', parsedPacket.alt, 'and (m): ', parsedPacket.alt/3.2808, '\n'
        print 'Comment: ', parsedPacket.comment, '\n'


    def getCall(self, parsedPacket):
        return parsedPacket.callsign

    def newPacket(self):
        new = Packet('', '', 1000.0, 1000.0, 0.0, 0.0, 0.0, '')
        return new


