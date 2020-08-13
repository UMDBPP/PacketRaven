from datetime import datetime
import unittest

import numpy

from huginn.packets import APRSLocationPacket
from huginn.structures import DoublyLinkedList
from huginn.tracks import APRSTrack


class TestDoublyLinkedList(unittest.TestCase):
    def test_index(self):
        list_1 = DoublyLinkedList([0, 5, 4, 'foo', 5, 6])

        assert list_1[0] == 0
        assert list_1[0] is list_1.head.value
        assert list_1[3] == 'foo'
        assert list_1[-2] == 5
        assert list_1[-1] == 6
        assert list_1[-1] is list_1.tail.value

    def test_length(self):
        list_1 = DoublyLinkedList()

        assert len(list_1) == 0

        list_2 = DoublyLinkedList([0, 'foo'])

        assert len(list_2) == 2

    def test_extend(self):
        list_1 = DoublyLinkedList([0])
        list_1.extend(['foo', 5])

        assert list_1 == [0, 'foo', 5]
        assert list_1.head is not list_1.tail

    def test_append(self):
        list_1 = DoublyLinkedList()
        list_1.append(0)

        assert list_1[0] == 0
        assert list_1[-1] == 0
        assert list_1.head is list_1.tail

    def test_insert(self):
        list_1 = DoublyLinkedList([0, 'foo'])
        list_1.insert('bar', 0)

        assert list_1 == ['bar', 0, 'foo']

    def test_equality(self):
        list_1 = DoublyLinkedList([5, 4, 'foo'])

        assert list_1 == [5, 4, 'foo']
        assert list_1 == (5, 4, 'foo')
        assert list_1 != [5, 4, 'foo', 6, 2]

    def test_remove(self):
        list_1 = DoublyLinkedList(['a', 'a'])
        list_1.remove('a')

        assert len(list_1) == 0
        assert list_1.head is None
        assert list_1.tail is None

        list_2 = DoublyLinkedList(['a', 'b', 'c'])
        del list_2[0]
        del list_2[-1]

        assert len(list_2) == 1
        assert list_2[0] == 'b'
        assert list_2[-1] == 'b'

        list_3 = DoublyLinkedList([0, 5, 4, 'foo', 0, 0])
        list_3.remove(0)

        assert list_3 == [5, 4, 'foo']
        assert list_3[0] == 5
        assert list_3[-1] == 'foo'


class TestPackets(unittest.TestCase):
    def test_from_raw_aprs(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))

        assert numpy.all(packet_1.coordinates == (-77.48778502911327, 39.64903419561805, 16341.5472))
        assert packet_1['callsign'] is packet_1['from']
        assert packet_1['callsign'] == 'W3EAX-13'
        assert packet_1['comment'] == "|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu"

    def test_equality(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 38, 23))
        packet_4 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))

        assert packet_2 != packet_1
        assert packet_3 == packet_1
        assert packet_4 != packet_1

    def test_subtraction(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 38, 23))

        packet_delta = packet_2 - packet_1

        assert packet_delta.seconds == 127
        assert packet_delta.vertical_distance == -2243.0231999999996
        assert packet_delta.horizontal_distance == 4019.3334763155167


class TestPacketTracks(unittest.TestCase):
    def test_append(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu")

        track = APRSTrack('W3EAX-13')

        track.append(packet_1)
        track.append(packet_2)
        self.assertRaises(ValueError, track.append, packet_3)

        assert track[0] is packet_1
        assert track[1] is packet_2
        assert track[-1] is packet_2

    def test_values(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))

        track = APRSTrack('W3EAX-13', [packet_1])

        assert numpy.all(track.coordinates[-1] == packet_1.coordinates)

    def test_rates(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 39, 28))

        track = APRSTrack('W3EAX-13', [packet_1, packet_2, packet_3])

        assert track.ascent_rate[1] == (packet_2 - packet_1).ascent_rate
        assert track.ground_speed[1] == (packet_2 - packet_1).ground_speed

    def test_sorting(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 39, 28))

        track = APRSTrack('W3EAX-13', [packet_2, packet_1, packet_3])

        assert sorted(track) == [packet_1, packet_2, packet_3]


if __name__ == '__main__':
    unittest.main()
