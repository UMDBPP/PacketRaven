"""
Ground track class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

from data_structures import aprs_packet


class GroundTrack:
    def __init__(self, callsign: str):
        """
        Instantiate GroundTrack object with initial conditions.

        :param callsign: Callsign of ground track.
        """

        self.callsign = callsign
        self.packets = []

    def add_packet(self, packet: aprs_packet.APRSPacket):
        if packet.callsign is self.callsign:
            self.packets.append(packet)
        else:
            print(f'Packet callsign {packet.callsign} does not match ground track callsign {self.callsign}.')

    def ascent_rate(self) -> float:
        """
        Calculate ascent rate.

        :return: ascent rate in meters per second
        """

        # TODO implement filtering
        delta = self.packets[-1] - self.packets[-2]
        return delta.vertical_distance / delta.seconds

    def ground_speed(self) -> float:
        """
        Calculate ground speed.

        :return: ground speed in meters per second
        """

        # TODO implement filtering
        delta = self.packets[-1] - self.packets[-2]
        return delta.horizontal_distance / delta.seconds

    def seconds_to_impact(self, num_packets: int = 3) -> float:
        """
        Calculate seconds to reach the ground.

        :return: seconds to impact
        """

        current_ascent_rate = self.ascent_rate()

        if current_ascent_rate < 0:
            most_recent_packet = self.packets[-1]  # why -1?

            # TODO implement landing location as the intersection of the predicted descent track with a local DEM
            # TODO implement a time to impact calc based off of standard atmo
            return most_recent_packet.altitude / current_ascent_rate
        else:
            return -1

    def downrange_distance(self, longitude, latitude) -> float:
        """
        Calculate overground distance from the most recent packet to a given point.

        :return: distance to point in meters
        """

        most_recent_packet = self.packets[-1]

        return most_recent_packet.distance_to_point(longitude, latitude)

    def __str__(self) -> str:
        return f'APRS ground track {self.callsign}'


if __name__ == '__main__':
    aprs_packet_1 = aprs_packet.APRSPacket(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,KM4LKM:!/:h=W;%E1O   /A=000095|!!|  /W3EAX,16,8,22'C,http://www.umd.edu")
    aprs_packet_2 = aprs_packet.APRSPacket(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,KM4LKM:!/:GwN:cNCO   /A=000564|!-|  /W3EAX,75,8,5'C,http://www.umd.edu")

    ground_track = GroundTrack('W3EAX-8')
    ground_track.add_packet(aprs_packet_1)
    ground_track.add_packet(aprs_packet_2)

    print(f'Ascent rate: {ground_track.ascent_rate()}')
    print(f'Ground speed: {ground_track.ground_speed()}')
