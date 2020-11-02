from datetime import datetime
from functools import partial
import os
import unittest

import psycopg2
from sshtunnel import SSHTunnelForwarder
from tablecrow.table import random_open_tcp_port, split_URL_port
from tablecrow.tables.postgres import PostGresTable, SSH_DEFAULT_PORT, database_has_table

from packetraven.connections import APRSDatabaseTable, APRSfi
from packetraven.packets import APRSPacket
from packetraven.utilities import read_configuration, repository_root

CREDENTIALS_FILENAME = repository_root() / 'credentials.config'


class TestAPRS(unittest.TestCase):
    def test_aprs_fi(self):
        balloon_callsigns = ['W3EAX-10', 'W3EAX-11', 'W3EAX-13', 'W3EAX-14']

        credentials = read_configuration(CREDENTIALS_FILENAME)
        if 'aprs_fi' not in credentials:
            credentials['aprs_fi'] = {'api_key': os.environ['APRS_FI_API_KEY']}

        aprs_api = APRSfi(balloon_callsigns, credentials['aprs_fi']['api_key'])

        packets = aprs_api.packets

        assert all(type(packet) is APRSPacket for packet in packets)


class TestPostGres(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        credentials = read_configuration(CREDENTIALS_FILENAME)

        if 'database' not in credentials:
            credentials['database'] = {
                'hostname': os.environ['POSTGRES_HOSTNAME'],
                'database': os.environ['POSTGRES_DATABASE'],
                'username': os.environ['POSTGRES_USERNAME'],
                'password': os.environ['POSTGRES_PASSWORD']
            }
            if 'ssh_hostname' in os.environ:
                credentials['database']['ssh_hostname'] = os.environ['SSH_HOSTNAME']
            if 'ssh_username' in os.environ:
                credentials['database']['ssh_username'] = os.environ['SSH_USERNAME']
            if 'ssh_password' in os.environ:
                credentials['database']['ssh_password'] = os.environ['SSH_PASSWORD']

        self.hostname = credentials['database']['hostname']
        self.database = credentials['database']['database']
        self.username = credentials['database']['username']
        self.password = credentials['database']['password']

        self.ssh_hostname = credentials['database']['ssh_hostname'] if 'ssh_hostname' in credentials['database'] else None
        self.ssh_username = credentials['database']['ssh_username'] if 'ssh_username' in credentials['database'] else None
        self.ssh_password = credentials['database']['ssh_password'] if 'ssh_password' in credentials['database'] else None

        hostname, port = split_URL_port(self.hostname)
        if port is None:
            port = PostGresTable.DEFAULT_PORT

        connector = partial(psycopg2.connect, database=self.database, user=self.username, password=self.password)
        if self.ssh_hostname is not None:
            ssh_hostname, ssh_port = split_URL_port(self.ssh_hostname)
            if ssh_port is None:
                ssh_port = SSH_DEFAULT_PORT

            if '@' in ssh_hostname:
                ssh_username, ssh_hostname = ssh_hostname.split('@', 1)

            ssh_username = self.ssh_username

            if ssh_username is not None and ':' in ssh_username:
                ssh_username, ssh_password = ssh_hostname.split(':', 1)

            ssh_password = self.ssh_password

            self.tunnel = SSHTunnelForwarder((ssh_hostname, ssh_port),
                                             ssh_username=ssh_username, ssh_password=ssh_password,
                                             remote_bind_address=('localhost', port),
                                             local_bind_address=('localhost', random_open_tcp_port()))
            try:
                self.tunnel.start()
            except Exception as error:
                raise ConnectionError(error)
            self.connection = connector(host=self.tunnel.local_bind_host, port=self.tunnel.local_bind_port)
        else:
            self.tunnel = None
            self.connection = connector(host=hostname, port=port)

    def test_packet_database(self):
        table_name = 'test_table'

        packet_1 = APRSPacket.from_frame("W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   "
                                         "/A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
                                         packet_time=datetime(2019, 2, 3, 14, 36, 16))
        packet_2 = APRSPacket.from_frame("W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   "
                                         "/A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
                                         packet_time=datetime(2019, 2, 3, 14, 38, 23))
        packet_3 = APRSPacket.from_frame("W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   "
                                         "/A=043080|!j|  /W3EAX,326,0,20'C,nearspace.umd.edu",
                                         packet_time=datetime(2019, 2, 3, 14, 39, 28))

        input_packets = [packet_1, packet_2, packet_3]

        with self.connection as connection:
            with connection.cursor() as cursor:
                if database_has_table(cursor, table_name):
                    cursor.execute(f'DROP TABLE {table_name};')

        packet_table = APRSDatabaseTable(hostname=self.hostname, database=self.database, table=table_name,
                                         username=self.username, password=self.password,
                                         ssh_hostname=self.ssh_hostname, ssh_username=self.ssh_username, ssh_password=self.ssh_password)
        packet_table.insert(input_packets)

        assert packet_1 == packet_table[packet_1.time, packet_1.from_callsign]

        packets = packet_table.packets

        with self.connection as connection:
            with connection.cursor() as cursor:
                assert database_has_table(cursor, table_name)
                cursor.execute(f'DROP TABLE {table_name};')

        assert len(packets) > 0 and all(packets[packet_index] == input_packets[packet_index]
                                        for packet_index in range(len(packets)))


if __name__ == '__main__':
    unittest.main()
