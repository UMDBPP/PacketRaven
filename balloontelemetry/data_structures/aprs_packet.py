"""
APRS packet class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import datetime

import aprslib
from haversine import haversine


class APRSPacketDelta:
    def __init__(self, seconds: float, horizontal_distance: float, vertical_distance: float):
        self.seconds = seconds
        self.horizontal_distance = horizontal_distance
        self.vertical_distance = vertical_distance

    def ascent_rate(self):
        # TODO implement filtering
        if self.seconds > 0:
            if self.vertical_distance > 0:
                return self.vertical_distance / self.seconds
            else:
                return 0
        else:
            raise ValueError('Packets have the same timestamp.')

    def ground_speed(self):
        # TODO implement filtering
        if self.seconds > 0:
            if self.horizontal_distance > 0:
                return self.horizontal_distance / self.seconds
            else:
                return 0
        else:
            raise ValueError('Packets have the same timestamp.')

    def __str__(self) -> str:
        return f'APRS packet delta: {self.seconds} seconds, {self.horizontal_distance} meters overground, {self.vertical_distance} meters vertically'


class APRSPacket:
    def __init__(self, raw_packet: str, packet_datetime: datetime.datetime = None):
        """
        Construct APRS packet object from raw packet and given datetime.

        :param raw_packet: String containing raw packet.
        :param packet_datetime: Datetime of packet, either as datetime object, seconds since epoch, or string in ISO format.
        """

        self.raw = raw_packet

        # aprslib converts units to metric
        parsed_packet = aprslib.parse(self.raw)

        if packet_datetime is not None:
            if type(packet_datetime) in [int, float]:
                self.packet_datetime = datetime.datetime.fromtimestamp(packet_datetime)
            elif type(packet_datetime) is str:
                self.packet_datetime = datetime.datetime.fromisoformat(packet_datetime)
            else:
                self.packet_datetime = packet_datetime
        elif 'timestamp' in parsed_packet:
            self.packet_datetime = datetime.datetime.fromtimestamp(int(parsed_packet['timestamp']))
        else:
            self.packet_datetime = datetime.datetime.now()

        self.callsign = parsed_packet['from']
        self.longitude = parsed_packet['longitude']
        self.latitude = parsed_packet['latitude']
        self.altitude = parsed_packet['altitude']
        self.comment = parsed_packet['comment']

        # heading is degrees clockwise from north
        self.heading = parsed_packet['course'] if 'course' in parsed_packet else None
        self.ground_speed = parsed_packet['speed'] if 'speed' in parsed_packet else None

    def distance_to_point(self, longitude, latitude) -> float:
        # TODO implement WGS84 distance
        return haversine((self.latitude, self.longitude), (latitude, longitude), unit='m')

    def __sub__(self, other) -> APRSPacketDelta:
        seconds = (self.packet_datetime - other.packet_datetime).total_seconds()
        horizontal_distance = self.distance_to_point(other.longitude, other.latitude)
        vertical_distance = self.altitude - other.altitude

        return APRSPacketDelta(seconds, horizontal_distance, vertical_distance)

    def __str__(self) -> str:
        return f'APRS packet: {self.callsign} {self.packet_datetime} ({self.longitude}, {self.latitude}, {self.altitude}) "{self.comment}"'


if __name__ == '__main__':
    import datetime

    packet_1 = APRSPacket(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
        packet_datetime=datetime.datetime(2018, 11, 11, 10, 20, 13))
    packet_2 = APRSPacket(
        "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
        packet_datetime=datetime.datetime(2018, 11, 11, 10, 21, 24))
    packet_delta = packet_2 - packet_1

    print(f'Packet 1: {packet_1}')
    print(f'Packet 2: {packet_2}')
    print(f'Packet delta: {packet_delta}')
