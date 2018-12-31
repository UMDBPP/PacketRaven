
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

   Declares ground track container & handler class. Takes over derived quantity
   calculation from Packet itself; also does a whole lot more quantities. Also
   separates out ground tracks from different callsigns.
*/
"""


class DecodedPacket:
    """
    Structure containing decoded data from APRS location packets.
    Also has a constructor for easy assignment.
    Convention: Time: YYYY-MM-DD HH:MM:SS, Negative latitude is South, Negative longitude is West,
    altitude is in feet, heading is degrees clockwise from North, speed is in Knots, ascent rate is ft/s.
    """

    def __init__(self,cs,ts,_lat,_lon,_alt,_heading,_speed,cmt):
        self.callsign = cs
        self.timestamp = ts
        self.lat = _lat
        self.lon = _lon
        self.alt = _alt
        self.heading = _heading
        self.speed = _speed
        self.comment = cmt


