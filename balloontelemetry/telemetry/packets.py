"""
APRS packet class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import datetime
import math

import aprslib
import haversine


class LocationPacket:
    """
    4D location packet, containing longitude, latitude, altitude, and time.
    """

    def __init__(self, time: datetime.datetime, longitude: float, latitude: float, altitude: float):
        self.time = time
        self.longitude = longitude
        self.latitude = latitude
        self.altitude = altitude

    class Delta:
        def __init__(self, seconds: float, horizontal_distance: float, vertical_distance: float):
            self.seconds = seconds
            self.vertical_distance = vertical_distance
            self.horizontal_distance = horizontal_distance

            if seconds > 0:
                self.ascent_rate = self.vertical_distance / self.seconds
                self.ground_speed = self.horizontal_distance / self.seconds
            else:
                self.ascent_rate = math.inf
                self.ground_speed = math.inf

        def __str__(self) -> str:
            return f'{self.seconds} s, {self.vertical_distance:6.2f} m vertical, {self.horizontal_distance:6.2f} m horizontal'

    def coordinates(self, z: bool = False) -> tuple:
        """
        Return coordinates.

        :param z: Whether to include altitude as third entry in tuple.
        :return: tuple of coordinates (lon, lat[, alt])
        """

        if z:
            return self.longitude, self.latitude, self.altitude
        else:
            return self.longitude, self.latitude

    def distance_to_point(self, longitude, latitude) -> float:
        # TODO implement WGS84 distance
        return haversine.haversine((self.latitude, self.longitude), (latitude, longitude), unit='m')

    def __sub__(self, other) -> Delta:
        """
        Return subtraction of packets in the form of Delta object.

        :param other: Packet object
        :return: Delta object
        """

        seconds = (self.time - other.time).total_seconds()
        horizontal_distance = self.distance_to_point(other.longitude, other.latitude)
        vertical_distance = self.altitude - other.altitude

        return self.Delta(seconds, horizontal_distance, vertical_distance)

    def __eq__(self, other) -> bool:
        """
        Whether this packet equals another packet, ignoring datetime (because of possible staggered duplicate packets).

        :param other: Packet to compare to this one.
        :return: equality
        """

        return self.longitude == other.longitude and self.latitude == other.latitude and self.altitude == other.altitude

    def __str__(self):
        return f'{self.time} ({self.longitude:.3f}, {self.latitude:.3f}, {self.altitude:.2f})'


class APRS(LocationPacket):
    """
    APRS packet containing parsed APRS fields, along with location and time.
    """

    def __init__(self, raw_aprs: str, time: datetime.datetime = None):
        """
        Construct APRS packet object from raw packet and given datetime.

        :param raw_aprs: String containing raw packet.
        :param time: Time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        # aprslib converts units to metric
        parsed_packet = aprslib.parse(raw_aprs)

        # TODO make HABduino add timestamp to packet upon transmission
        if time is not None:
            if type(time) in [int, float]:
                # assume Unix epoch
                time = datetime.datetime.fromtimestamp(time)
            elif type(time) is str:
                # assume ISO format date string
                time = datetime.datetime.fromisoformat(time)
        elif 'timestamp' in parsed_packet:
            # extract time from Unix epoch
            time = datetime.datetime.fromtimestamp(float(parsed_packet['timestamp']))
        else:
            # otherwise default to time the packet was received (now)
            time = datetime.datetime.now()

        super().__init__(time, parsed_packet['longitude'], parsed_packet['latitude'],
                         parsed_packet['altitude'])

        self.raw_packet = raw_aprs
        self.parsed_packet = parsed_packet

    def __getitem__(self, field: str):
        """
        Indexing function (for string indexing of APRS fields).

        :param field: APRS field name
        :return: value of field
        """

        if field == 'callsign':
            field = 'from'

        return self.parsed_packet[field]

    def __eq__(self, other) -> bool:
        """
        Whether this packet equals another packet, including callsign and comment.

        :param other: Packet to compare to this one.
        :return: equality
        """

        return super().__eq__(other) and self['callsign'] == other['callsign'] and self['comment'] == other['comment']

    def __str__(self) -> str:
        return f'{super().__str__()} {self["callsign"]} "{self["comment"]}"'


if __name__ == '__main__':
    packet_1 = APRS(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
        time='2018-11-11T10:20:13')
    packet_2 = APRS(
        "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
        time='2018-11-11T10:21:24')
    packet_delta = packet_2 - packet_1

    print(f'Packet 1: {packet_1}')
    print(f'Packet 2: {packet_2}')
    print(f'Packet delta: {packet_delta}')
