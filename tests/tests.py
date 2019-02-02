"""
Unit tests for balloon telemetry package.

__authors__ = ['Zachary Burnett']
"""

import datetime
import unittest

from huginn.ground_track import data_structures
from huginn.ground_track import ground_track
from huginn.telemetry import packets
from huginn.telemetry import parsing


class TestDoublyLinkedList(unittest.TestCase):
    def test_getitem(self):
        list_1 = data_structures.DoublyLinkedList([0, 5, 4, 'foo', 5, 6])

        self.assertEqual(0, list_1[0])
        self.assertEqual(0, list_1.head.value)
        self.assertEqual('foo', list_1[3])
        self.assertEqual(6, list_1[-1])
        self.assertEqual(6, list_1.tail.value)

    def test_len(self):
        list_1 = data_structures.DoublyLinkedList()
        list_2 = data_structures.DoublyLinkedList([0, 'foo'])

        self.assertEqual(0, len(list_1))
        self.assertEqual(2, len(list_2))

    def test_extend(self):
        list_1 = data_structures.DoublyLinkedList([0])
        list_1.extend(['foo', 5])

        self.assertEqual([0, 'foo', 5], list_1)
        self.assertTrue(list_1.head is not list_1.tail)

    def test_append(self):
        list_1 = data_structures.DoublyLinkedList()
        list_1.append(0)

        self.assertEqual(0, list_1[0])
        self.assertEqual(0, list_1[-1])
        self.assertTrue(list_1.head is list_1.tail)

    def test_insert(self):
        list_1 = data_structures.DoublyLinkedList([0, 'foo'])
        list_1.insert('bar', 0)

        self.assertEqual(['bar', 0, 'foo'], list_1)

    def test_remove(self):
        list_1 = data_structures.DoublyLinkedList(['a', 'a'])
        list_2 = data_structures.DoublyLinkedList(['a', 'b', 'c'])
        list_3 = data_structures.DoublyLinkedList([0, 5, 4, 'foo', 0, 0])

        list_1.remove('a')
        del list_2[0]
        del list_2[-1]
        list_3.remove(0)

        self.assertEqual(0, len(list_1))
        self.assertTrue(list_1.head is None)
        self.assertTrue(list_1.tail is None)
        self.assertEqual(1, len(list_2))
        self.assertEqual('b', list_2[0])
        self.assertEqual('b', list_2[-1])
        self.assertEqual([5, 4, 'foo'], list_3)
        self.assertEqual(5, list_3[0])
        self.assertEqual('foo', list_3[-1])


class TestPackets(unittest.TestCase):
    def test_aprs(self):
        packet = packets.APRS(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:20:13')

        self.assertEqual(datetime.datetime(2018, 11, 11, 10, 20, 13), packet.time)
        self.assertEqual((-77.90921071284187, 39.7003564996876, 8201.8632), packet.coordinates(z=True))
        self.assertTrue(packet['callsign'] is packet['from'])
        self.assertEqual('W3EAX-8', packet['callsign'])
        self.assertEqual('|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu', packet['comment'])

    def test_equality(self):
        packet_1 = packets.APRS(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:20:13')
        packet_2 = packets.APRS(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:21:24')
        packet_3 = packets.APRS(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:21:31')

        self.assertTrue(packet_1 != packet_2)
        self.assertTrue(packet_1 == packet_3)

    def test_subtraction(self):
        packet_1 = packets.APRS(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:20:13')
        packet_2 = packets.APRS(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:21:24')

        packet_delta = packet_2 - packet_1

        self.assertEqual(71, packet_delta.seconds)
        self.assertEqual(443.78880000000026, packet_delta.vertical_distance)
        self.assertEqual(2408.700970494594, packet_delta.horizontal_distance)


class TestGroundTrack(unittest.TestCase):
    def test_append(self):
        packet_1 = packets.APRS(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:20:13')
        packet_2 = packets.APRS(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:21:24')

        track = ground_track.GroundTrack('W3EAX-8')

        track.append(packet_1)
        track.append(packet_2)

        self.assertTrue(track[0] is packet_1)
        self.assertTrue(track[1] is packet_2)

    def test_rates(self):
        packet = packets.APRS(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:20:13')

        track = ground_track.GroundTrack('W3EAX-8')

        track.append(packet)

        self.assertEqual(packet.altitude, track.altitude())
        self.assertEqual(packet.coordinates(), track.coordinates())
        self.assertEqual(packet.altitude, track.altitude())

    def test_values(self):
        packet_1 = packets.APRS(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:20:13')
        packet_2 = packets.APRS(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
            time='2018-11-11T10:21:24')

        track = ground_track.GroundTrack('W3EAX-8', [packet_1, packet_2])

        self.assertEqual((packet_2 - packet_1).ascent_rate, track.ascent_rate())
        self.assertEqual((packet_2 - packet_1).ground_speed, track.ground_speed())


class TestParser(unittest.TestCase):
    def test_parse_aprs_packet(self):
        parsed_packet = parsing.parse_aprs_packet(
            'W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu')

        self.assertEqual('W3EAX-8', parsed_packet['from'])
        self.assertEqual(-77.90921071284187, parsed_packet['longitude'])
        self.assertEqual(39.7003564996876, parsed_packet['latitude'])
        self.assertEqual(8201.8632, parsed_packet['altitude'])
        self.assertEqual('|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu', parsed_packet['comment'])


if __name__ == '__main__':
    unittest.main()
