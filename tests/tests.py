import datetime
import unittest

from balloontelemetry.ground_track import data_structures
from balloontelemetry.ground_track import ground_track
from balloontelemetry.telemetry import packets
from balloontelemetry.telemetry import parsing


class TestDoublyLinkedList(unittest.TestCase):
    def test_len(self):
        empty_list = data_structures.DoublyLinkedList()
        nonempty_list = data_structures.DoublyLinkedList([0, 'foo'])

        self.assertEqual(0, len(empty_list))
        self.assertEqual(2, len(nonempty_list))

    def test_extend(self):
        extended_list = data_structures.DoublyLinkedList([0])
        extended_list.extend(['foo', 5])

        self.assertEqual([0, 'foo', 5], extended_list)
        self.assertTrue(extended_list.head is not extended_list.tail)

    def test_append(self):
        appended_list = data_structures.DoublyLinkedList()
        appended_list.append(0)

        self.assertEqual(0, appended_list[0])
        self.assertEqual(0, appended_list[-1])
        self.assertTrue(appended_list.head is appended_list.tail)

    def test_insert(self):
        inserted_list = data_structures.DoublyLinkedList([0, 'foo'])
        inserted_list.insert('bar', 0)

        self.assertEqual(['bar', 0, 'foo'], inserted_list)

    def test_remove(self):
        removed_list = data_structures.DoublyLinkedList([0, 5, 4, 'foo', 0, 0])

        removed_list.remove(0)

        self.assertEqual([5, 4, 'foo'], removed_list)
        self.assertEqual(5, removed_list.head.value)
        self.assertEqual('foo', removed_list.tail.value)


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
