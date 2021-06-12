from datetime import datetime, timedelta
from typing import Iterable, Union

from dateutil.parser import parse as parse_date
import numpy
from pandas import DataFrame
from pyproj import CRS

from packetraven.model import (
    FREEFALL_DESCENT_RATE,
    FREEFALL_DESCENT_RATE_UNCERTAINTY,
    FREEFALL_SECONDS_TO_GROUND,
)
from packetraven.packets import APRSPacket, DEFAULT_CRS, LocationPacket
from packetraven.packets.structures import DoublyLinkedList


class LocationPacketTrack:
    """ collection of location packets """

    def __init__(self, name: str, packets: [LocationPacket] = None, crs: CRS = None):
        """
        location packet track

        :param name: name of packet track
        :param crs: coordinate reference system to use
        :param packets: iterable of packets
        """

        self.name = name
        self.packets = DoublyLinkedList(None)
        self.crs = crs if crs is not None else DEFAULT_CRS

        if packets is not None:
            for packet in packets:
                self.append(packet)

    def append(self, packet: LocationPacket):
        if packet not in self.packets:
            if packet.crs != self.crs:
                packet.transform_to(self.crs)
            self.packets.append(packet)

    def extend(self, packets: [LocationPacket]):
        for packet in packets:
            self.append(packet)

    def sort(self):
        self.packets.sort()

    @property
    def times(self) -> numpy.ndarray:
        return numpy.array([packet.time for packet in self.packets], dtype=numpy.datetime64)

    @property
    def coordinates(self) -> numpy.ndarray:
        return numpy.stack([packet.coordinates for packet in self.packets], axis=0)

    @property
    def altitudes(self) -> numpy.ndarray:
        return self.coordinates[:, 2]

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
    def overground_distances(self) -> numpy.ndarray:
        """ overground distances between packets """
        return numpy.concatenate(
            [
                [0],
                numpy.array(
                    [packet_delta.overground for packet_delta in self.packets.difference]
                ),
            ]
        )

    @property
    def ascents(self) -> numpy.ndarray:
        """ differences in altitude between packets """
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
        """ instantaneous ascent rates between packets """
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
        """ instantaneous overground speeds between packets """
        return numpy.concatenate(
            [
                [0],
                numpy.array(
                    [packet_delta.ground_speed for packet_delta in numpy.diff(self.packets)]
                ),
            ]
        )

    @property
    def cumulative_overground_distances(self) -> numpy.ndarray:
        """ cumulative overground distances from start """
        return numpy.cumsum(self.overground_distances)

    @property
    def time_to_ground(self) -> timedelta:
        """ estimated time to reach the ground at the current rate of descent """

        current_ascent_rate = self.ascent_rates[-1]
        if current_ascent_rate < 0:
            # TODO implement landing location as the intersection of the predicted descent track with a local DEM
            # TODO implement a time to impact calc based off of standard atmo
            return timedelta(seconds=self.altitudes[-1] / abs(current_ascent_rate))
        else:
            return timedelta(seconds=-1)

    @property
    def distance_downrange(self) -> float:
        """ direct overground distance between first and last packets only """
        if len(self.packets) > 0:
            return self.packets[-1].overground_distance(self.coordinates[0, :2])
        else:
            return 0.0

    @property
    def length(self) -> float:
        """ total length of the packet track over the ground """
        return sum([distance.overground for distance in self.packets.difference])

    def __getitem__(
        self, index: Union[int, Iterable[int], slice]
    ) -> Union[LocationPacket, 'LocationPacketTrack']:
        if isinstance(index, int):
            return self.packets[index]
        elif isinstance(index, Iterable) or isinstance(index, slice):
            if isinstance(index, numpy.ndarray) and index.dtype == bool:
                index = numpy.where(index)[0]
            if isinstance(index, slice) or len(index) > 0:
                packets = self.packets[index]
            else:
                packets = None
            return self.__class__(self.name, packets, self.crs)
        else:
            raise ValueError(f'unrecognized index: {index}')

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

    @property
    def dataframe(self) -> DataFrame:
        return DataFrame(
            {
                'name': [self.name for _ in range(len(self))],
                'times': self.times,
                'x': self.coordinates[:, 0],
                'y': self.coordinates[:, 1],
                'z': self.coordinates[:, 2],
                'intervals': self.intervals,
                'overground_distances': self.overground_distances,
                'ascents': self.ascents,
                'ascent_rates': self.ascent_rates,
                'ground_speeds': self.ground_speeds,
                'cumulative_overground_distances': self.cumulative_overground_distances,
            }
        )


class BalloonTrack(LocationPacketTrack):
    def __init__(self, name: str, packets: [LocationPacket] = None, crs: CRS = None):
        super().__init__(name, packets, crs)
        self.__falling = False

    @property
    def time_to_ground(self) -> timedelta:
        current_ascent_rate = self.ascent_rates[-1]
        if current_ascent_rate < 0:
            if self.falling:
                return timedelta(seconds=FREEFALL_SECONDS_TO_GROUND(self.altitudes[-1]))
            else:
                current_altitude = self.altitudes[-1]
                # TODO implement landing location as the intersection of the predicted descent track with a local DEM
                return timedelta(seconds=current_altitude / -current_ascent_rate)
        else:
            return timedelta(seconds=-1)

    @property
    def falling(self) -> bool:
        current_ascent_rate = self.ascent_rates[-1]
        if current_ascent_rate >= 0:
            self.__falling = False
        elif not self.__falling:
            current_altitude = self.altitudes[-1]
            freefall_descent_rate = FREEFALL_DESCENT_RATE(current_altitude)
            freefall_descent_rate_uncertainty = FREEFALL_DESCENT_RATE_UNCERTAINTY(
                current_altitude
            )
            if numpy.abs(current_ascent_rate - freefall_descent_rate) < numpy.abs(
                freefall_descent_rate_uncertainty
            ):
                self.__falling = True
        return self.__falling


class APRSTrack(BalloonTrack):
    """ collection of APRS location packets """

    def __init__(self, callsign: str, packets: [APRSPacket] = None, crs: CRS = None):
        """
        APRS packet track

        :param callsign: callsign of APRS packets
        :param packets: iterable of packets
        :param crs: coordinate reference system to use
        """

        if not isinstance(callsign, str):
            callsign = str(callsign)
        if len(callsign) > 9 or ' ' in callsign:
            raise ValueError(f'unrecognized callsign format: "{callsign}"')

        self.__callsign = callsign
        super().__init__(self.callsign, packets, crs)

    @property
    def callsign(self) -> str:
        return self.__callsign

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


class PredictedTrajectory(LocationPacketTrack):
    def __init__(
        self, name: str, packets: [LocationPacket], prediction_time: datetime, crs: CRS = None
    ):
        """
        prediction trajectory

        :param name: name of prediction
        :param packets: iterable of packets
        :param prediction_time: time of prediction
        :param crs: coordinate reference system to use
        """

        if isinstance(prediction_time, str):
            prediction_time = parse_date(prediction_time)

        super().__init__(name, packets, crs)
        self.prediction_time = prediction_time

    @property
    def landing_site(self) -> (float, float, float):
        return self.coordinates[-1]
