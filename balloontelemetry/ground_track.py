"""
Ground track class for packet operations.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

from balloontelemetry import aprs_packet


class GroundTrack:
    def __init__(self, callsign: str):
        """
        Instantiate GroundTrack object with initial conditions.

        :param callsign: Callsign of ground track.
        """

        self.callsign = callsign
        self.packets = []

    def add_packet(self, raw_packet: str):
        self.packets.append(aprs_packet.APRSPacket(raw_packet))

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
            most_recent_packet = self.packets[-1]

            # TODO implement landing location as the intersection of the predicted descent track with a local DEM
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
