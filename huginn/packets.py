"""
APRS packet class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import math
from datetime import datetime
from typing import Union

from haversine import haversine

from huginn.parsing import parse_raw_aprs


class LocationPacket:
    """ 4D location packet, containing longitude, latitude, altitude, and time """

    def __init__(self, time: datetime, longitude: float, latitude: float, altitude: float = None):
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

    @property
    def coordinates(self) -> (float, float, float):
        """
        geographic coordinates of this packet

        :return: tuple of coordinates (lon, lat, alt)
        """

        return self.longitude, self.latitude, self.altitude

    def distance_to_point(self, longitude, latitude) -> float:
        # TODO implement WGS84 distance
        return haversine((self.latitude, self.longitude), (latitude, longitude), unit='m')

    def __sub__(self, other) -> Delta:
        """
        Return subtraction of packets in the form of Delta object.

        :param other: location packet
        :return: Delta object
        """

        seconds = (self.time - other.time).total_seconds()
        horizontal_distance = self.distance_to_point(other.longitude, other.latitude)
        vertical_distance = self.altitude - other.altitude

        return self.Delta(seconds, horizontal_distance, vertical_distance)

    def __eq__(self, other) -> bool:
        """
        Whether this packet equals another packet, ignoring datetime (because of possible staggered duplicate packets).

        :param other: packet to compare to this one
        :return: equality
        """

        return self.longitude == other.longitude and self.latitude == other.latitude and self.altitude == other.altitude

    def __gt__(self, other) -> bool:
        """
        Whether this packet is after another packet in time.

        :param other: packet to compare to this one
        :return: whether this packet occurred after the other
        """

        return self.time > other.time

    def __lt__(self, other) -> bool:
        """
        Whether this packet is before another packet in time.

        :param other: packet to compare to this one
        :return: whether this packet occurred before the other
        """

        return self.time < other.time

    def __str__(self) -> str:
        return f'{self.time} ({self.longitude:.3f}, {self.latitude:.3f}, {self.altitude:.2f})'


class APRSLocationPacket(LocationPacket):
    """ APRS packet containing parsed APRS fields, along with location and time """

    def __init__(self, raw_aprs: Union[str, bytes, dict], time: datetime = None):
        """
        APRS packet object from raw packet and given datetime

        :param raw_aprs: string containing raw packet
        :param time: Time of packet, either as datetime object, seconds since Unix epoch, or ISO format date string.
        """

        # parse packet with metric units
        parsed_packet = parse_raw_aprs(raw_aprs)

        if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
            if time is None:
                if 'timestamp' in parsed_packet:
                    # extract time from Unix epoch
                    time = datetime.fromtimestamp(float(parsed_packet['timestamp']))
                else:
                    # TODO make HABduino add timestamp to packet upon transmission
                    # otherwise default to time the packet was received (now)
                    time = datetime.now()

            super().__init__(time, parsed_packet['longitude'], parsed_packet['latitude'],
                             parsed_packet['altitude'] if 'altitude' in parsed_packet else None)
            self.parsed_packet = parsed_packet
        else:
            raise ValueError(f'Input packet does not contain location data: {raw_aprs}')

    @property
    def callsign(self) -> str:
        return self['callsign']

    def __getitem__(self, field: str):
        if field == 'callsign':
            field = 'from'

        if self.__contains__(field):
            return self.parsed_packet[field]
        else:
            raise KeyError(f'Packet does not contain the field "{field}"')

    def __contains__(self, field: str):
        """
        whether packet contains the given APRS field

        :param field: APRS field name
        :return: whether field exists
        """

        if field == 'callsign':
            field = 'from'

        return field in self.parsed_packet

    def __eq__(self, other) -> bool:
        """
        whether this packet equals another packet, including callsign and comment

        :param other: packet to compare to this one
        :return: equality
        """

        return super().__eq__(other) and self['callsign'] == other['callsign'] and self['comment'] == other['comment']

    def __str__(self) -> str:
        return f'{self["callsign"]} {super().__str__()} "{self["comment"]}"'

    def __repr__(self) -> str:
        return str(self)
