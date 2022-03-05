from copy import copy
from datetime import datetime, timedelta
from os import PathLike
from typing import Any, Dict, Iterable, List, Union

from dateutil.parser import parse as parse_date
import geojson
import numpy
from pandas import DataFrame
from pyproj import CRS

from packetraven.model import (
    FREEFALL_DESCENT_RATE,
    FREEFALL_DESCENT_RATE_UNCERTAINTY,
    FREEFALL_SECONDS_TO_GROUND,
)
from packetraven.packets import APRSPacket, DEFAULT_CRS, LocationPacket
from packetraven.packets.base import Distance
from packetraven.packets.structures import DoublyLinkedList


class LocationPacketTrack:
    """
    a collection of location packets in chronological order
    """

    def __init__(
        self,
        packets: List[LocationPacket] = None,
        name: str = None,
        crs: CRS = None,
        **attributes,
    ):
        """
        :param packets: iterable of packets
        :param name: name of packet track
        :param crs: coordinate reference system to use
        """

        if name is None:
            name = 'packet track'
        elif not isinstance(name, str):
            name = str(name)

        self.name = name
        self.packets = DoublyLinkedList(None)
        self.crs = crs if crs is not None else DEFAULT_CRS
        self.attributes = attributes

        if packets is not None:
            self.extend(packets)

        self.__length = len(self)
        self.__data = None

    def append(self, packet: LocationPacket):
        if packet not in self.packets:
            if packet.crs != self.crs:
                packet.transform_to(self.crs)
            self.packets.append(packet)

    def extend(self, packets: List[LocationPacket]):
        for packet in packets:
            self.append(packet)

    def sort(self, inplace: bool = False):
        if inplace:
            instance = self
        else:
            instance = copy(self)
        instance.packets.sort(inplace=True)
        return instance

    @property
    def data(self) -> DataFrame:
        if self.__data is None or len(self) != self.__length:
            records = [
                {
                    'time': packet.time,
                    'x': packet.coordinates[0],
                    'y': packet.coordinates[1],
                    'altitude': packet.coordinates[2],
                }
                for packet in self.packets
            ]
            for index, packet_delta in enumerate(
                numpy.insert(numpy.diff(self.packets), 0, Distance(0, 0, 0, self.crs))
            ):
                records[index].update(
                    {
                        'interval': packet_delta.interval,
                        'overground_distance': packet_delta.overground,
                        'ascent': packet_delta.ascent,
                        'ground_speed': packet_delta.ground_speed,
                        'ascent_rate': packet_delta.ascent_rate,
                    }
                )

            self.__data = DataFrame.from_records(records)

        return self.__data

    @property
    def times(self) -> numpy.ndarray:
        return self.data['time'].values

    @property
    def coordinates(self) -> numpy.ndarray:
        return self.data[['x', 'y', 'altitude']].values

    @property
    def altitudes(self) -> numpy.ndarray:
        return self.coordinates[:, -1]

    @property
    def intervals(self) -> numpy.ndarray:
        return self.data['interval'].values

    @property
    def overground_distances(self) -> numpy.ndarray:
        """ overground distances between packets """
        return self.data['overground_distance'].values

    @property
    def ascents(self) -> numpy.ndarray:
        """ differences in altitude between packets """
        return self.data['ascent'].values

    @property
    def ascent_rates(self) -> numpy.ndarray:
        """ instantaneous ascent rates between packets """
        return self.data['ascent_rate'].values

    @property
    def ground_speeds(self) -> numpy.ndarray:
        """ instantaneous overground speeds between packets """
        return self.data['ground_speed'].values

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
        if isinstance(index, str):
            try:
                index = parse_date(index)
            except:
                index = int(index)
        if isinstance(index, int):
            return self.packets[index]
        elif isinstance(index, Iterable) or isinstance(index, slice):
            if isinstance(index, numpy.ndarray) and index.dtype == bool:
                index = numpy.where(index)[0]
            if isinstance(index, slice) or len(index) > 0:
                packets = self.packets[index]
            else:
                packets = None
            return self.__class__(packets=packets, crs=self.crs, **self.attributes)
        elif isinstance(index, (datetime, numpy.datetime64)):
            if not isinstance(index, numpy.datetime64):
                index = numpy.datetime64(index)
            matching_packets = []
            for packet in self.packets:
                if packet.time == index:
                    matching_packets.append(packet)
            if len(matching_packets) == 0:
                maximum_interval = max(self.intervals)
                if (
                    index > min(self.times) - maximum_interval
                    and index < max(self.times) + maximum_interval
                ):
                    smallest_difference = None
                    closest_time = None
                    for packet in self.packets:
                        packet_time = numpy.datetime64(packet.time)
                        difference = abs(packet_time - index)
                        if smallest_difference is None or difference < smallest_difference:
                            smallest_difference = difference
                            closest_time = packet_time
                    return self[closest_time]
                else:
                    raise IndexError(
                        f'time index out of range: {min(self.times) - maximum_interval} <\= {index} <\= {max(self.times) + maximum_interval}'
                    )
            elif len(matching_packets) == 1:
                return matching_packets[0]
            else:
                return self.__class__(packets=matching_packets, name=self.name, crs=self.crs)
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
        return self.packets == other.packets and self.attributes == other.attributes

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

    @classmethod
    def from_file(cls, filename: PathLike) -> List['LocationPacketTrack']:
        """
        load packet tracks from the given file

        :param filename: file path to GeoJSON
        :return: packet tracks
        """

        with open(filename) as input_file:
            data = geojson.load(input_file)

        points = []
        linestrings = []
        for feature in data['features']:
            if feature['geometry']['type'] == 'Point':
                points.append(feature)
            elif feature['geometry']['type'] == 'LineString':
                linestrings.append(feature)

        tracks = []
        for linestring in linestrings:
            packets = []
            for coordinate in linestring['geometry']['coordinates']:
                for index, point in enumerate(points):
                    if point['geometry']['coordinates'] == coordinate:
                        packet = LocationPacket(
                            x=point['geometry']['coordinates'][0],
                            y=point['geometry']['coordinates'][1],
                            z=point['geometry']['coordinates'][2],
                            **point['properties'],
                        )
                        packets.append(packet)
                        if index != 0:
                            points.pop(index)
                        break
            track = LocationPacketTrack(packets=packets, **linestring['properties'])

            tracks.append(track)

        return tracks


class BalloonTrack(LocationPacketTrack):
    """
    a packet track describing the path of a balloon
    """

    def __init__(
        self,
        packets: List[LocationPacket] = None,
        name: str = None,
        crs: CRS = None,
        **attributes,
    ):
        LocationPacketTrack.__init__(self, packets=packets, name=name, crs=crs, **attributes)
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
    """
    a balloon track comprised of APRS packets
    """

    def __init__(
        self,
        packets: List[APRSPacket] = None,
        callsign: str = None,
        crs: CRS = None,
        **attributes,
    ):
        """
        :param packets: iterable of packets
        :param callsign: callsign of APRS packets
        :param crs: coordinate reference system to use
        """

        if 'name' not in attributes:
            attributes['name'] = 'APRS track'

        if callsign is not None:
            if not isinstance(callsign, str):
                callsign = str(callsign)
            if len(callsign) > 9 or ' ' in callsign:
                raise ValueError(f'unrecognized callsign format: "{callsign}"')

        BalloonTrack.__init__(self, packets=packets, callsign=callsign, crs=crs, **attributes)

    @property
    def callsign(self) -> str:
        return self.attributes['callsign']

    def append(self, packet: APRSPacket):
        packet_callsign = packet['callsign']

        if self.callsign is None or packet_callsign == self.callsign:
            super().append(packet)
        else:
            raise ValueError(
                f'Packet callsign {packet_callsign} does not match ground track callsign {self.callsign}.'
            )

    def __str__(self) -> str:
        return f'{self.callsign}: {super().__str__()}'

    @classmethod
    def from_file(cls, filename: PathLike) -> List['APRSTrack']:
        tracks = LocationPacketTrack.from_file(filename)

        for index in range(len(tracks)):
            track = tracks[index]
            packets = []
            for packet in track.packets:
                packets.append(
                    APRSPacket(
                        from_callsign=packet.attributes['from'],
                        to_callsign=packet.attributes['to'],
                        time=packet.time,
                        x=packet.coordinates[0],
                        y=packet.coordinates[1],
                        z=packet.coordinates[2],
                        **{
                            key: value
                            for key, value in packet.attributes.items()
                            if key not in ['from', 'to']
                        },
                    )
                )
            tracks[index] = APRSTrack(packets=packets, crs=track.crs, **track.attributes)

        return tracks


class PredictedTrajectory(LocationPacketTrack):
    """
    a prediction trajectory retrieved from a prediction API
    """

    def __init__(
        self,
        packets: List[LocationPacket],
        parameters: Dict[str, Any],
        metadata: Dict[str, Any],
        crs: CRS = None,
        **attributes,
    ):
        """
        :param packets: iterable of packets
        :param parameters: prediction parameters
        :param metadata: prediction completion metadata
        :param crs: coordinate reference system to use
        """

        if 'name' not in attributes:
            attributes['name'] = 'predicted trajectory'

        self.__parameters = parameters
        self.__metadata = metadata

        LocationPacketTrack.__init__(
            self, packets=packets, crs=crs, **attributes,
        )

    @property
    def landing_site(self) -> (float, float, float):
        return self.coordinates[-1]

    @classmethod
    def from_file(cls, filename: PathLike) -> List['PredictedTrajectory']:
        tracks = LocationPacketTrack.from_file(filename)

        for index in range(len(tracks)):
            track = tracks[index]
            tracks[index] = PredictedTrajectory(
                packets=track.packets, crs=track.crs, **track.attributes,
            )

        return tracks

    @property
    def parameters(self) -> Dict[str, Any]:
        return self.__parameters

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.__metadata
