"""
Unit tests for balloon telemetry package.

__authors__ = ['Zachary Burnett']
"""

import datetime

import pytest

from huginn import tracks, structures, parsing, packets


class TestDoublyLinkedList():
    def test_getitem(self):
        list_1 = structures.DoublyLinkedList([0, 5, 4, 'foo', 5, 6])

        assert list_1[0] == 0
        assert list_1.head.value == 0
        assert list_1[3] == 'foo'
        assert list_1[-1] == 6
        assert list_1.tail.value == 6

    def test_len(self):
        list_1 = structures.DoublyLinkedList()
        list_2 = structures.DoublyLinkedList([0, 'foo'])

        assert len(list_1) == 0
        assert len(list_2) == 2

    def test_extend(self):
        list_1 = structures.DoublyLinkedList([0])
        list_1.extend(['foo', 5])

        assert list_1 == [0, 'foo', 5]
        assert list_1.head is not list_1.tail

    def test_append(self):
        list_1 = structures.DoublyLinkedList()
        list_1.append(0)

        assert list_1[0] == 0
        assert list_1[-1] == 0
        assert list_1.head is list_1.tail

    def test_insert(self):
        list_1 = structures.DoublyLinkedList([0, 'foo'])
        list_1.insert('bar', 0)

        assert list_1 == ['bar', 0, 'foo']

    def test_remove(self):
        list_1 = structures.DoublyLinkedList(['a', 'a'])
        list_2 = structures.DoublyLinkedList(['a', 'b', 'c'])
        list_3 = structures.DoublyLinkedList([0, 5, 4, 'foo', 0, 0])

        list_1.remove('a')
        del list_2[0]
        del list_2[-1]
        list_3.remove(0)

        assert len(list_1) == 0
        assert list_1.head is None
        assert list_1.tail is None
        assert len(list_2) == 1
        assert list_2[0] == 'b'
        assert list_2[-1] == 'b'
        assert list_3 == [5, 4, 'foo']
        assert list_3[0] == 5
        assert list_3[-1] == 'foo'


class TestPackets():
    def test_aprs_init(self):
        packet_1 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 20, 13))

        assert packet_1.coordinates() == (-77.90921071284187, 39.7003564996876, 8201.8632)
        assert packet_1['callsign'] is packet_1['from']
        assert packet_1['callsign'] == 'W3EAX-8'
        assert packet_1['comment'] == '|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu'

    def test_equality(self):
        packet_1 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            datetime.datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 21, 24))
        packet_3 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 21, 31))
        packet_4 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 20, 13))

        assert packet_2 != packet_1
        assert packet_3 == packet_1
        assert packet_4 != packet_1

    def test_subtraction(self):
        packet_1 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 21, 24))

        packet_delta = packet_2 - packet_1

        assert packet_delta.seconds == 71
        assert packet_delta.vertical_distance == 443.78880000000026
        assert packet_delta.horizontal_distance == 2408.700970494594


class TestPacketTracks():
    def test_append(self):
        packet_1 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 21, 24))

        track = tracks.APRSTrack('W3EAX-8')

        track.append(packet_1)
        track.append(packet_2)

        assert track[0] is packet_1
        assert track[1] is packet_2

    def test_rates(self):
        packet_1 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 20, 13))

        track = tracks.APRSTrack('W3EAX-8')

        track.append(packet_1)

        assert track.altitude() == packet_1.altitude
        assert track.coordinates() == packet_1.coordinates()
        assert track.altitude() == packet_1.altitude

    def test_values(self):
        packet_1 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = packets.APRSLocationPacket(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time=datetime.datetime(2018, 11, 11, 10, 21, 24))

        track = tracks.APRSTrack('W3EAX-8', [packet_1, packet_2])

        assert track.ascent_rate() == (packet_2 - packet_1).ascent_rate
        assert track.ground_speed() == (packet_2 - packet_1).ground_speed


class TestParser():
    def test_parse_aprs_packet(self):
        parsed_packet = parsing.parse_aprs_packet(
            'W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu')

        assert parsed_packet['from'] == 'W3EAX-8'
        assert parsed_packet['longitude'] == -77.90921071284187
        assert parsed_packet['latitude'] == 39.7003564996876
        assert parsed_packet['altitude'] == 8201.8632
        assert parsed_packet['comment'] == '|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu'

    def test_partial_packets(self):
        with pytest.raises(parsing.PartialPacketError):
            parsing.parse_aprs_packet('W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,KM4LKM')

        with pytest.raises(parsing.PartialPacketError):
            parsing.parse_aprs_packet('W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:')
