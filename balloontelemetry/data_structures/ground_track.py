"""
Ground track class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

from balloontelemetry.data_structures import aprs_packet


class GroundTrack:
    def __init__(self, callsign: str):
        """
        Instantiate GroundTrack object with initial conditions.

        :param callsign: Callsign of ground track.
        """

        self.callsign = callsign
        self.packets = []

    def add_packet(self, packet: aprs_packet.APRSPacket):
        if packet.callsign == self.callsign:
            # TODO check if packet is a duplicate
            self.packets.append(packet)
        else:
            print(f'Packet callsign {packet.callsign} does not match ground track callsign {self.callsign}.')

    def altitude(self) -> float:
        """
        Return altitude of most recent packet.

        :return: altitude in meters
        """

        return self.packets[-1].altitude

    def coordinates(self, z: bool = False) -> tuple:
        """
        Return coordinates of most recent packet.

        :param z: Whether to include altitude as third entry in tuple.
        :return: tuple of coordinates (lon, lat[, alt])
        """

        return self.packets[-1].coordinates(z)

    def ascent_rate(self) -> float:
        """
        Calculate ascent rate.

        :return: ascent rate in meters per second
        """

        if len(self.packets) >= 2:
            # TODO implement filtering
            return (self.packets[-1] - self.packets[-2]).ascent_rate
        else:
            raise ValueError('Not enough packets to process request.')

    def ground_speed(self) -> float:
        """
        Calculate ground speed.

        :return: ground speed in meters per second
        """

        if len(self.packets) >= 2:
            # TODO implement filtering
            return (self.packets[-1] - self.packets[-2]).ground_speed
        else:
            raise ValueError('Not enough packets to process request.')

    def seconds_to_impact(self) -> float:
        """
        Calculate seconds to reach the ground.

        :return: seconds to impact
        """

        current_ascent_rate = self.ascent_rate()

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

        if len(self.packets) >= 1:
            return self.packets[-1].distance_to_point(longitude, latitude)
        else:
            raise ValueError('Not enough packets to process request.')

    def __str__(self) -> str:
        return f'APRS ground track {self.callsign}'


if __name__ == '__main__':
    import datetime

    packet_1 = aprs_packet.APRSPacket(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
        packet_datetime=datetime.datetime(2018, 11, 11, 10, 20, 13))
    packet_2 = aprs_packet.APRSPacket(
        "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
        packet_datetime=datetime.datetime(2018, 11, 11, 10, 21, 24))

    ground_track = GroundTrack('W3EAX-8')
    ground_track.add_packet(packet_1)
    ground_track.add_packet(packet_2)

    print(f'Altitude: {ground_track.altitude()} m')
    print(f'Ascent rate: {ground_track.ascent_rate()} m/s')
    print(f'Ground speed: {ground_track.ground_speed()} m/s')
