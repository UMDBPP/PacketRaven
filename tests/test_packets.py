from datetime import datetime
import unittest

import numpy

from packetraven.packets import APRSPacket
from packetraven.tracks import APRSTrack


class TestPackets(unittest.TestCase):
    def test_from_raw_aprs(self):
        packet_1 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))

        assert numpy.allclose(packet_1.coordinates, (-77.48778502911327, 39.64903419561805, 16341.5472))
        assert packet_1['callsign'] is packet_1['from']
        assert packet_1['callsign'] == 'W3EAX-13'
        assert packet_1['comment'] == "|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu"

    def test_equality(self):
        packet_1 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSPacket.from_frame(
            "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 38, 23))
        packet_4 = APRSPacket.from_frame(
            "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))

        assert packet_2 != packet_1
        assert packet_3 == packet_1
        assert packet_4 != packet_1

    def test_subtraction(self):
        packet_1 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSPacket.from_frame(
            "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 38, 23))

        packet_delta = packet_2 - packet_1

        assert packet_delta.seconds == 127
        assert numpy.allclose(packet_delta.ascent, -2243.0231999999996)
        assert numpy.allclose(packet_delta.distance, 4019.3334763155167)


class TestPacketTracks(unittest.TestCase):
    def test_append(self):
        packet_1 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSPacket.from_frame(
            "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSPacket.from_frame(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu")

        track = APRSTrack('W3EAX-13')

        track.append(packet_1)
        track.append(packet_2)
        self.assertRaises(ValueError, track.append, packet_3)

        assert track[0] is packet_1
        assert track[1] is packet_2
        assert track[-1] is packet_2

    def test_values(self):
        packet_1 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))

        track = APRSTrack('W3EAX-13', [packet_1])

        assert numpy.all(track.coordinates[-1] == packet_1.coordinates)

    def test_rates(self):
        packet_1 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSPacket.from_frame(
            "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSPacket.from_frame(
            "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 39, 28))

        track = APRSTrack('W3EAX-13', [packet_1, packet_2, packet_3])

        assert track.ascent_rates[1] == (packet_2 - packet_1).ascent_rate
        assert track.ground_speeds[1] == (packet_2 - packet_1).ground_speed

    def test_sorting(self):
        packet_1 = APRSPacket.from_frame(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSPacket.from_frame(
            "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSPacket.from_frame(
            "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,"
            "nearspace.umd.edu",
            packet_time=datetime(2019, 2, 3, 14, 39, 28))

        track = APRSTrack('W3EAX-13', [packet_2, packet_1, packet_3])

        assert sorted(track) == [packet_1, packet_2, packet_3]
