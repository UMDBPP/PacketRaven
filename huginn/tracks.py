"""
Ground track class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

from typing import Union

import numpy

from huginn.packets import APRSLocationPacket, LocationPacket
from huginn.structures import DoublyLinkedList


class LocationPacketTrack:
    """ collection of location packets """

    def __init__(self, packets: [LocationPacket] = None):
        """
        location packet track

        :param packets: iterable of packets
        """

        self.packets = DoublyLinkedList(packets)

    def append(self, packet: LocationPacket):
        if packet not in self.packets:
            self.packets.append(packet)

    @property
    def time(self) -> numpy.array:
        """ 1D array of packet date times """
        return numpy.array([packet.time for packet in self.packets], dtype=numpy.datetime64)

    @property
    def coordinates(self) -> numpy.array:
        """ N x 3 array of geographic coordinates and meter altitude """
        return numpy.stack((packet.coordinates for packet in self.packets), axis=0)

    @property
    def ascent_rate(self) -> numpy.array:
        """ 1D array of ascent rate (m/s) """
        return numpy.insert(numpy.array([packet_delta.ascent_rate for packet_delta in numpy.diff(self.packets)]), 0, 0)

    @property
    def ground_speed(self) -> numpy.array:
        """ 1D array of ground speed (m/s) """
        return numpy.insert(numpy.array([packet_delta.ground_speed for packet_delta in numpy.diff(self.packets)]), 0, 0)

    @property
    def seconds_to_impact(self) -> float:
        """ seconds to reach the ground at the current ascent rate """

        current_ascent_rate = self.ascent_rate[-1]

        if current_ascent_rate < 0:
            # TODO implement landing location as the intersection of the predicted descent track with a local DEM
            # TODO implement a time to impact calc based off of standard atmo
            return self.packets[-1].z / current_ascent_rate
        else:
            return -1

    def downrange_distance(self, longitude, latitude) -> float:
        """
        overground distance from the most recent packet to a given point

        :return: distance to point in meters
        """

        if len(self.packets) > 0:
            return self.packets[-1].horizontal_distance_to_point(longitude, latitude)
        else:
            return 0.0

    def __getitem__(self, index: Union[int, slice]) -> LocationPacket:
        return self.packets[index]

    def __iter__(self):
        return iter(self.packets)

    def __reversed__(self):
        return reversed(self.packets)

    def __contains__(self, item) -> bool:
        return item in self.packets

    def __len__(self) -> int:
        return len(self.packets)

    def __eq__(self, other) -> bool:
        return self.packets == other.packets

    def __str__(self) -> str:
        return str(list(self))


class APRSTrack(LocationPacketTrack):
    """ collection of APRS location packets """

    def __init__(self, callsign: str, packets: [APRSLocationPacket] = None):
        """
        APRS packet track

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
            raise ValueError(f'Packet callsign {packet_callsign} does not match ground track callsign {self.callsign}.')

    def __eq__(self, other) -> bool:
        return self.callsign == other.callsign and super().__eq__(other)

    def __str__(self) -> str:
        return f'{self.callsign}: {super().__str__()}'
