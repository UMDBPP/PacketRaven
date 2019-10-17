"""
Ground track class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import logging
from typing import Union

from huginn.packets import LocationPacket, APRSLocationPacket
from huginn.structures import DoublyLinkedList


class LocationPacketTrack:
    def __init__(self, packets=None):
        """
        Location packet track.

        :param packets: iterable of packets
        """

        self.packets = DoublyLinkedList(packets)

    def append(self, packet: LocationPacket):
        self.packets.append(packet)

    @property
    def longitude(self):
        return self.longitude

    @property
    def latitude(self):
        return self.latitude

    @property
    def altitude(self):
        return self.altitude

    @property
    def coordinates(self):
        return self.coordinates

    @property
    def ascent_rate(self):
        return self.ascent_rate

    @property
    def ground_speed(self):
        return self.ground_speed

    @property
    def seconds_to_impact(self):
        return self.seconds_to_impact

    @longitude.getter
    def longitude(self) -> float:
        """
        longitude of the most recent packet in this track

        :return: longitude
        """

        return self.packets[-1].longitude

    @latitude.getter
    def latitude(self) -> float:
        """
        latitude of the most recent packet in this track

        :return: latitude
        """

        return self.packets[-1].latitude

    @altitude.getter
    def altitude(self) -> float:
        """
        altitude of the most recent packet in this track

        :return: altitude in meters
        """

        return self.packets[-1].altitude

    @coordinates.getter
    def coordinates(self) -> (float, float, float):
        """
        geographic coordinates of the most recent packet in this track

        :return: tuple of coordinates (lon, lat[, alt])
        """

        return self.packets[-1].coordinates

    @ascent_rate.getter
    def ascent_rate(self) -> float:
        """
        most recent ascent rate of this track, in m/s

        :return: ascent rate in meters per second
        """

        if len(self.packets) > 1:
            # TODO implement filtering
            return (self.packets[-1] - self.packets[-2]).ascent_rate
        else:
            return 0.0

    @ground_speed.getter
    def ground_speed(self) -> float:
        """
        most recent speed over the ground of this track, in m/s

        :return: ground speed in meters per second
        """

        if len(self.packets) > 1:
            # TODO implement filtering
            return (self.packets[-1] - self.packets[-2]).ground_speed
        else:
            return 0.0

    @seconds_to_impact.getter
    def seconds_to_impact(self) -> float:
        """
        seconds until to reach the ground at the current ascent rate

        :return: seconds to impact
        """

        current_ascent_rate = self.ascent_rate

        if current_ascent_rate < 0:
            # TODO implement landing location as the intersection of the predicted descent track with a local DEM
            # TODO implement a time to impact calc based off of standard atmo
            return self.packets[-1].altitude / current_ascent_rate
        else:
            return -1

    def downrange_distance(self, longitude, latitude) -> float:
        """
        Calculate overground distance from the most recent packet to a given point.

        :return: distance to point in meters
        """

        if len(self.packets) > 0:
            return self.packets[-1].distance_to_point(longitude, latitude)
        else:
            return 0.0

    def __getitem__(self, index: Union[int, slice]) -> LocationPacket:
        """
        Indexing function (for integer indexing of packets).

        :param index: index
        :return: packet at index
        """

        return self.packets[index]

    def __iter__(self):
        return iter(self.packets)

    def __reversed__(self):
        return reversed(self.packets)

    def __len__(self) -> int:
        return len(self.packets)

    def __eq__(self, other) -> bool:
        return self.packets == other.packets

    def __str__(self) -> str:
        return str(list(self))


class APRSTrack(LocationPacketTrack):
    def __init__(self, callsign: str, packets=None):
        """
        APRS packet track.

        :param callsign: callsign of APRS packets
        :param packets: iterable of packets
        """

        self.callsign = callsign
        super().__init__(packets)

    def append(self, packet: APRSLocationPacket):
        packet_callsign = packet['callsign']

        if packet_callsign == self.callsign:
            super().append(packet)
        else:
            logging.warning(f'Packet callsign {packet_callsign} does not match ground track callsign {self.callsign}.')

    def __eq__(self, other) -> bool:
        return self.callsign == other.callsign and super().__eq__(other)

    def __str__(self) -> str:
        return f'{self.callsign}: {super().__str__()}'
