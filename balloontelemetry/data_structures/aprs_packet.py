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

    def __str__(self) -> str:
        return f'APRS packet delta: {self.seconds} seconds, {self.horizontal_distance} meters overground, {self.vertical_distance} meters vertically'


class APRSPacket:
    def __init__(self, raw_packet: str):
        self.raw = raw_packet

        # aprslib converts units to metric
        parsed_packet = aprslib.parse(self.raw)

        if 'timestamp' in parsed_packet:
            self.datetime = datetime.datetime.fromtimestamp(int(parsed_packet['timestamp']))
        else:
            self.datetime = datetime.datetime.now()

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
        seconds = (self.datetime - other.datetime).total_seconds()
        horizontal_distance = self.distance_to_point(other.longitude, other.latitude)
        vertical_distance = self.altitude - other.altitude

        return APRSPacketDelta(seconds, horizontal_distance, vertical_distance)

    def __str__(self) -> str:
        return f'APRS packet: {self.callsign} {self.datetime} ({self.longitude}, {self.latitude}, {self.altitude}) "{self.comment}"'


if __name__ == '__main__':
    packet_1 = APRSPacket(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,KM4LKM:!/:h=W;%E1O   /A=000095|!!|  /W3EAX,16,8,22'C,http://www.umd.edu")
    packet_2 = APRSPacket(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,KM4LKM:!/:GwN:cNCO   /A=000564|!-|  /W3EAX,75,8,5'C,http://www.umd.edu")
    packet_delta = packet_2 - packet_1

    print(packet_1)
    print(packet_2)
    print(packet_delta)
