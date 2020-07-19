"""
Unit tests for balloon telemetry package.

__authors__ = ['Zachary Burnett']
"""

from datetime import datetime
import os
from tempfile import TemporaryDirectory
import unittest

import numpy
import psycopg2

from huginn import CREDENTIALS_FILENAME, read_configuration
from huginn.connections import APRSPacketDatabaseTable, APRS_fi
from huginn.database import database_has_table
from huginn.packets import APRSLocationPacket
from huginn.parsing import PartialPacketError, parse_raw_aprs
from huginn.structures import DoublyLinkedList
from huginn.tracks import APRSTrack
from huginn.writer import write_aprs_packet_tracks


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
    def test_aprs_init(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))

        assert packet_1.coordinates == (-77.90921071284187, 39.7003564996876, 8201.8632)
        assert packet_1['callsign'] is packet_1['from']
        assert packet_1['callsign'] == 'W3EAX-8'
        assert packet_1['comment'] == '|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu'

    def test_equality(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu", datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))
        packet_3 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 31))
        packet_4 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))

        assert packet_2 != packet_1
        assert packet_3 == packet_1
        assert packet_4 != packet_1

    def test_subtraction(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))

        packet_delta = packet_2 - packet_1

        assert packet_delta.seconds == 71
        assert packet_delta.vertical_distance == 443.78880000000026
        assert packet_delta.horizontal_distance == 2414.6947151021304


class TestPacketTracks(unittest.TestCase):
    def test_append(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))

        track = APRSTrack('W3EAX-8')

        track.append(packet_1)
        track.append(packet_2)

        assert track[0] is packet_1
        assert track[1] is packet_2
        assert track[-1] is packet_2

    def test_values(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))

        track = APRSTrack('W3EAX-8', [packet_1])

        assert numpy.all(track.coordinates[-1] == packet_1.coordinates)

    def test_rates(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))

        track = APRSTrack('W3EAX-8', [packet_1, packet_2])

        assert track.ascent_rate[-1] == (packet_2 - packet_1).ascent_rate
        assert track.ground_speed[-1] == (packet_2 - packet_1).ground_speed

    def test_sorting(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))
        track = APRSTrack('W3EAX-8', [packet_2, packet_1])

        assert sorted(track) == [packet_1, packet_2]


class TestParser(unittest.TestCase):
    def test_parse_aprs_packet(self):
        parsed_packet = parse_raw_aprs('W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu')

        assert parsed_packet['from'] == 'W3EAX-8'
        assert parsed_packet['longitude'] == -77.90921071284187
        assert parsed_packet['latitude'] == 39.7003564996876
        assert parsed_packet['altitude'] == 8201.8632
        assert parsed_packet['comment'] == '|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu'

    def test_partial_packets(self):
        with self.assertRaises(PartialPacketError):
            parse_raw_aprs('W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,KM4LKM')

        with self.assertRaises(PartialPacketError):
            parse_raw_aprs('W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:')


class TestWriter(unittest.TestCase):
    def test_write_kml(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))

        track = APRSTrack('W3EAX-8', [packet_1, packet_2])

        with TemporaryDirectory() as temporary_directory:
            output_filename = os.path.join(temporary_directory, 'test_output.kml')
            write_aprs_packet_tracks([track], os.path.join(output_filename))
            assert os.path.exists(output_filename)

    def test_write_geojson(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))

        track = APRSTrack('W3EAX-8', [packet_1, packet_2])

        with TemporaryDirectory() as temporary_directory:
            output_filename = os.path.join(temporary_directory, 'test_output.geojson')
            write_aprs_packet_tracks([track], os.path.join(output_filename))
            assert os.path.exists(output_filename)


class TestConnections(unittest.TestCase):
    def test_aprs_fi(self):
        balloon_callsigns = ['W3EAX-10', 'W3EAX-11', 'W3EAX-14']

        credentials = read_configuration(CREDENTIALS_FILENAME)
        api_key = credentials['APRS_FI']['api_key']

        aprs_api = APRS_fi(balloon_callsigns, api_key)

        with aprs_api:
            packets = aprs_api.packets

        assert all(type(packet) is APRSLocationPacket for packet in packets)

    def test_packet_database(self):
        balloon_callsigns = ['W3EAX-10', 'W3EAX-11', 'W3EAX-14']

        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,http://www.umd.edu",
                                                    time=datetime(2018, 11, 11, 10, 21, 24))

        credentials = read_configuration(CREDENTIALS_FILENAME)

        packet_table = APRSPacketDatabaseTable(**credentials['DATABASE'])

        with packet_table:
            packet_table.insert([packet_1, packet_2])

        with packet_table:
            packets = packet_table.packets

        with psycopg2.connect(host=packet_table.hostname, port=packet_table.port, database=packet_table.database, user=packet_table.username,
                              password=packet_table.password) as connection:
            with connection.cursor() as cursor:
                assert database_has_table(cursor, packet_table.table)
                cursor.execute(f'DROP TABLE {packet_table.table};')

        assert len(packets) > 0 and all(type(packet) is APRSLocationPacket for packet in packets)


if __name__ == '__main__':
    unittest.main()
