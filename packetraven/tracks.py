from datetime import timedelta
from typing import Union

import numpy
from pyproj import CRS, Geod

from .packets import APRSPacket, DEFAULT_CRS, LocationPacket
from .structures import DoublyLinkedList


class LocationPacketTrack:
    """ collection of location packets """

    def __init__(self, packets: [LocationPacket] = None, crs: CRS = None):
        """
        location packet track

        :param crs: coordinate reference system to use
        :param packets: iterable of packets
        """

        self.packets = DoublyLinkedList(packets)
        self.crs = crs if crs is not None else DEFAULT_CRS

    def append(self, packet: LocationPacket):
        if packet not in self.packets:
            if packet.crs != self.crs:
                packet.transform_to(self.crs)
            self.packets.append(packet)

    @property
    def times(self) -> numpy.ndarray:
        return numpy.array([packet.time for packet in self.packets], dtype=numpy.datetime64)

    @property
    def coordinates(self) -> numpy.ndarray:
        return numpy.stack([packet.coordinates for packet in self.packets], axis=0)

    @property
    def intervals(self) -> numpy.ndarray:
        return numpy.concatenate(
            [
                [0],
                numpy.array(
                    [packet_delta.seconds for packet_delta in numpy.diff(self.packets)]
                ),
            ]
        )

    @property
    def distances(self) -> numpy.ndarray:
        return numpy.concatenate(
            [
                [0],
                numpy.array(
                    [packet_delta.distance for packet_delta in numpy.diff(self.packets)]
                ),
            ]
        )

    @property
    def ascents(self) -> numpy.ndarray:
        return numpy.concatenate(
            [
                [0],
                numpy.array(
                    [packet_delta.ascent for packet_delta in numpy.diff(self.packets)]
                ),
            ]
        )

    @property
    def ascent_rates(self) -> numpy.ndarray:
        return numpy.concatenate(
            [
                [0],
                numpy.array(
                    [packet_delta.ascent_rate for packet_delta in numpy.diff(self.packets)]
                ),
            ]
        )

    @property
    def ground_speeds(self) -> numpy.ndarray:
        return numpy.concatenate(
            [
                [0],
                numpy.array(
                    [packet_delta.ground_speed for packet_delta in numpy.diff(self.packets)]
                ),
            ]
        )

    @property
    def time_to_ground(self) -> timedelta:
        """ estimated time to reach the ground at the current ascent rate """

        current_ascent_rate = self.ascent_rates[-1]

        if current_ascent_rate < 0:
            # TODO implement landing location as the intersection of the predicted descent track with a local DEM
            # TODO implement a time to impact calc based off of standard atmo
            return timedelta(
                seconds=self.packets[-1].coordinates[2] / abs(current_ascent_rate)
            )
        else:
            return timedelta(seconds=-1)

    @property
    def distance_from_start(self) -> float:
        """ overground distance from the first to the most recent packet """

        if len(self.packets) > 0:
            return self.packets[-1].distance(self.coordinates[0, :2])
        else:
            return 0.0

    @property
    def length(self) -> float:
        """ total length of the packet track over the ground """

        coordinates = self.coordinates[:2]
        if self.crs.is_projected:
            return sum(self.packets.difference)
        else:
            ellipsoid = self.crs.datum.to_json_dict()['ellipsoid']
            geodetic = Geod(a=ellipsoid['semi_major_axis'], rf=ellipsoid['inverse_flattening'])
            return geodetic.line_length(coordinates[:, 0], coordinates[:, 1])

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

    def __init__(self, callsign: str, packets: [APRSPacket] = None, crs: CRS = None):
        """
        APRS packet track

        :param callsign: callsign of APRS packets
        :param packets: iterable of packets
        :param crs: coordinate reference system to use
        """

        self.callsign = callsign
        super().__init__(packets, crs)

    def append(self, packet: APRSPacket):
        packet_callsign = packet['callsign']

        if packet_callsign == self.callsign:
            super().append(packet)
        else:
            raise ValueError(
                f'Packet callsign {packet_callsign} does not match ground track callsign {self.callsign}.'
            )

    def __eq__(self, other) -> bool:
        return self.callsign == other.__callsign and super().__eq__(other)

    def __str__(self) -> str:
        return f'{self.callsign}: {super().__str__()}'
