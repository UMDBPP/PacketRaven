from datetime import datetime
from functools import partial
import os

import psycopg2
import pytest
from sshtunnel import SSHTunnelForwarder
from tablecrow.table import random_open_tcp_port, split_URL_port
from tablecrow.tables.postgres import PostGresTable, SSH_DEFAULT_PORT, database_has_table

from packetraven.connections import APRSDatabaseTable
from packetraven.packets import APRSPacket
from packetraven.utilities import read_configuration, repository_root

CREDENTIALS_FILENAME = repository_root() / 'credentials.config'
CREDENTIALS = read_configuration(CREDENTIALS_FILENAME)

if 'database' not in CREDENTIALS:
    CREDENTIALS['database'] = {}

default_credentials = {
    'hostname': ('POSTGRES_HOSTNAME', 'localhost'),
    'database': ('POSTGRES_DATABASE', 'postgres'),
    'username': ('POSTGRES_USERNAME', 'postgres'),
    'password': ('POSTGRES_PASSWORD', ''),
    'ssh_hostname': ('SSH_HOSTNAME', None),
    'ssh_username': ('SSH_USERNAME', None),
    'ssh_password': ('SSH_PASSWORD', None),
}

for credential, details in default_credentials.items():
    if credential not in CREDENTIALS['database']:
        CREDENTIALS['database'][credential] = os.getenv(*details)

if (
    'ssh_hostname' in CREDENTIALS['database']
    and CREDENTIALS['database']['ssh_hostname'] is not None
):
    hostname, port = split_URL_port(CREDENTIALS['database']['hostname'])
    if port is None:
        port = PostGresTable.DEFAULT_PORT

    ssh_hostname, ssh_port = split_URL_port(CREDENTIALS['database']['ssh_hostname'])
    if ssh_port is None:
        ssh_port = SSH_DEFAULT_PORT

    if '@' in ssh_hostname:
        ssh_username, ssh_hostname = ssh_hostname.split('@', 1)

    ssh_username = CREDENTIALS['database']['ssh_username']

    if ssh_username is not None and ':' in ssh_username:
        ssh_username, ssh_password = ssh_hostname.split(':', 1)

    ssh_password = CREDENTIALS['database']['ssh_password']

    TUNNEL = SSHTunnelForwarder(
        (ssh_hostname, ssh_port),
        ssh_username=ssh_username,
        ssh_password=ssh_password,
        remote_bind_address=('localhost', port),
        local_bind_address=('localhost', random_open_tcp_port()),
    )
    TUNNEL.start()
else:
    TUNNEL = None


@pytest.fixture
def connection() -> psycopg2.connect:
    hostname, port = split_URL_port(CREDENTIALS['database']['hostname'])
    if port is None:
        port = PostGresTable.DEFAULT_PORT

    connector = partial(
        psycopg2.connect,
        database=CREDENTIALS['database']['database'],
        user=CREDENTIALS['database']['username'],
        password=CREDENTIALS['database']['password'],
    )
    if tunnel := TUNNEL is not None:
        try:
            tunnel.start()
        except Exception as error:
            raise ConnectionError(error)
        connection = connector(host=tunnel.local_bind_host, port=tunnel.local_bind_port)
    else:
        connection = connector(host=hostname, port=port)

    return connection


def test_packet_database(connection):
    table_name = 'test_table'

    packet_1 = APRSPacket.from_frame(
        "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   "
        "/A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
        packet_time=datetime(2019, 2, 3, 14, 36, 16),
    )
    packet_2 = APRSPacket.from_frame(
        'W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   '
        "/A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
        packet_time=datetime(2019, 2, 3, 14, 38, 23),
    )
    packet_3 = APRSPacket.from_frame(
        'W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   '
        "/A=043080|!j|  /W3EAX,326,0,20'C,nearspace.umd.edu",
        packet_time=datetime(2019, 2, 3, 14, 39, 28),
    )

    input_packets = [packet_1, packet_2, packet_3]

    with connection:
        with connection.cursor() as cursor:
            if database_has_table(cursor, table_name):
                cursor.execute(f'DROP TABLE {table_name};')

    packet_table = APRSDatabaseTable(
        hostname=CREDENTIALS['database']['hostname'],
        database=CREDENTIALS['database']['database'],
        table=table_name,
        username=CREDENTIALS['database']['username'],
        password=CREDENTIALS['database']['password'],
        ssh_hostname=CREDENTIALS['database']['ssh_hostname'],
        ssh_username=CREDENTIALS['database']['ssh_username'],
        ssh_password=CREDENTIALS['database']['ssh_password'],
    )
    packet_table.insert(input_packets)

    assert packet_1 == packet_table[packet_1.time, packet_1.from_callsign]

    packets = packet_table.packets

    with connection:
        with connection.cursor() as cursor:
            assert database_has_table(cursor, table_name)
            cursor.execute(f'DROP TABLE {table_name};')

    assert len(packets) > 0 and all(
        packets[packet_index] == input_packets[packet_index]
        for packet_index in range(len(packets))
    )
