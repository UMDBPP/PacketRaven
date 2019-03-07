"""
APRS packet class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import datetime
import math

import haversine

from huginn import parsing


class LocationPacket:
    """
    4D location packet, containing longitude, latitude, altitude, and time.
    """

    def __init__(self, time: datetime.datetime, longitude: float, latitude: float, altitude: float = None):
        self.time = time
        self.longitude = longitude
        self.latitude = latitude
        self.altitude = altitude if altitude is not None else 0

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

        :param z: whether to include altitude as third entry in tuple
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

        :param other: location packet
        :return: Delta object
        """

        seconds = (self.time - other.time).total_seconds()
        horizontal_distance = self.distance_to_point(other.longitude, other.latitude)
        vertical_distance = abs(self.altitude - other.altitude)

        return self.Delta(seconds, horizontal_distance, vertical_distance)

    def __eq__(self, other) -> bool:
        """
        Whether this packet equals another packet, ignoring datetime (because of possible staggered duplicate packets).

        :param other: packet to compare to this one
        :return: equality
        """

        return self.longitude == other.longitude and self.latitude == other.latitude and self.altitude == other.altitude

    def __str__(self) -> str:
        return f'{self.time} ({self.longitude:.3f}, {self.latitude:.3f}, {self.altitude:.2f})'


class APRSPacket(LocationPacket):
    """
    APRS packet containing parsed APRS fields, along with location and time.
    """

    def __init__(self, raw_aprs: str, time: datetime.datetime = None):
        """
        Construct APRS packet object from raw packet and given datetime.

        :param raw_aprs: string containing raw packet
        :param time: Time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        # parse packet, units are metric
        parsed_packet = parsing.parse_aprs_packet(raw_aprs)

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

        if 'altitude' in parsed_packet:
            altitude = parsed_packet['altitude']
        else:
            altitude = None

        super().__init__(time, parsed_packet['longitude'], parsed_packet['latitude'], altitude)
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

        :param other: packet to compare to this one
        :return: equality
        """

        return super().__eq__(other) and self['callsign'] == other['callsign'] and self['comment'] == other['comment']

    def __str__(self) -> str:
        return f'{self["callsign"]} {super().__str__()} "{self["comment"]}"'

    def __repr__(self) -> str:
        return str(self)
