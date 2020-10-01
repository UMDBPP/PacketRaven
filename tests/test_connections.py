from datetime import datetime
import os
import unittest

from client import CREDENTIALS_FILENAME
from packetraven.connections import APRSPacketDatabaseTable, APRSfiConnection
from packetraven.database import database_has_table
from packetraven.packets import APRSLocationPacket
from packetraven.utilities import read_configuration


class TestAPRS_fi(unittest.TestCase):
    def test_aprs_fi(self):
        balloon_callsigns = ['W3EAX-10', 'W3EAX-11', 'W3EAX-13', 'W3EAX-14']

        credentials = read_configuration(CREDENTIALS_FILENAME)
        if 'aprs_fi' not in credentials:
            credentials['aprs_fi'] = {'api_key': os.environ['APRS_FI_API_KEY']}

        aprs_api = APRSfiConnection(balloon_callsigns, credentials['aprs_fi']['api_key'])

        with aprs_api:
            packets = aprs_api.packets

        assert all(type(packet) is APRSLocationPacket for packet in packets)


class TestDatabase(unittest.TestCase):
    def test_packet_database(self):
        packet_1 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,"
            "nearspace.umd.edu",
            time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
            time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,"
            "nearspace.umd.edu",
            time=datetime(2019, 2, 3, 14, 39, 28))

        input_packets = [packet_1, packet_2, packet_3]

        credentials = read_configuration(CREDENTIALS_FILENAME)

        if 'database' not in credentials:
            credentials['database'] = {
                'hostname': os.environ['POSTGRES_HOSTNAME'],
                'database': os.environ['POSTGRES_DATABASE'],
                'username': os.environ['POSTGRES_USERNAME'],
                'password': os.environ['POSTGRES_PASSWORD']
            }
            if 'ssh_hostname' in os.environ:
                credentials['database']['ssh_hostname'] = os.environ['ssh_hostname']
            if 'ssh_port' in os.environ:
                credentials['database']['ssh_port'] = os.environ['ssh_port']
            if 'ssh_username' in os.environ:
                credentials['database']['ssh_username'] = os.environ['ssh_username']
            if 'ssh_password' in os.environ:
                credentials['database']['ssh_password'] = os.environ['ssh_password']

        credentials['database']['table'] = 'test_table'

        packet_table = APRSPacketDatabaseTable(**credentials['database'], fields={field: str for field in packet_1})
        packet_table.insert(input_packets)

        assert packet_1 == packet_table[packet_1.time, packet_1.callsign]

        packets = packet_table.packets

        with packet_table.connection as connection:
            with connection.cursor() as cursor:
                assert database_has_table(cursor, packet_table.table)
                cursor.execute(f'DROP TABLE {packet_table.table};')

        assert len(packets) > 0 and all(packets[packet_index] == input_packets[packet_index]
                                        for packet_index in range(len(packets)))


if __name__ == '__main__':
    unittest.main()
