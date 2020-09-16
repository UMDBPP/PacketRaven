from datetime import datetime
import os
import unittest

from huginn import CREDENTIALS_FILENAME, read_configuration
from huginn.connections import APRSPacketDatabaseTable, APRS_fi
from huginn.database import database_has_table
from huginn.packets import APRSLocationPacket


class TestConnections(unittest.TestCase):
    def test_aprs_fi(self):
        balloon_callsigns = ['W3EAX-10', 'W3EAX-11', 'W3EAX-13', 'W3EAX-14']

        credentials = read_configuration(CREDENTIALS_FILENAME)
        if 'APRS_FI' not in credentials:
            credentials['APRS_FI'] = {'api_key': os.environ['APRS_FI_API_KEY']}

        aprs_api = APRS_fi(balloon_callsigns, credentials['APRS_FI']['api_key'])

        with aprs_api:
            packets = aprs_api.packets

        assert all(type(packet) is APRSLocationPacket for packet in packets)

    def test_packet_database(self):
        packet_1 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   /A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   /A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSLocationPacket.from_raw_aprs("W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,nearspace.umd.edu",
                                                    time=datetime(2019, 2, 3, 14, 39, 28))

        input_packets = [packet_1, packet_2, packet_3]

        credentials = read_configuration(CREDENTIALS_FILENAME)

        if 'DATABASE' not in credentials:
            credentials['DATABASE'] = {
                'hostname': os.environ['POSTGRES_HOSTNAME'],
                'database': os.environ['POSTGRES_DATABASE'],
                'username': os.environ['POSTGRES_USERNAME'],
                'password': os.environ['POSTGRES_PASSWORD']
            }
            if 'ssh_hostname' in os.environ:
                credentials['DATABASE']['ssh_hostname'] = os.environ['ssh_hostname']
            if 'ssh_port' in os.environ:
                credentials['DATABASE']['ssh_port'] = os.environ['ssh_port']
            if 'ssh_username' in os.environ:
                credentials['DATABASE']['ssh_username'] = os.environ['ssh_username']
            if 'ssh_password' in os.environ:
                credentials['DATABASE']['ssh_password'] = os.environ['ssh_password']

        credentials['DATABASE']['table'] = 'test_table'

        print(credentials['DATABASE'])

        packet_table = APRSPacketDatabaseTable(**credentials['DATABASE'], fields={field: str for field in packet_1})

        packet_table.insert(input_packets)

        packets = packet_table.packets

        with packet_table.connection as connection:
            with connection.cursor() as cursor:
                assert database_has_table(cursor, packet_table.table)
                cursor.execute(f'DROP TABLE {packet_table.table};')

        assert len(packets) > 0 and all(packets[packet_index] == input_packets[packet_index] for packet_index in range(len(packets)))


if __name__ == '__main__':
    unittest.main()
