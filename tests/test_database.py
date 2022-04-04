from datetime import datetime
import os

import psycopg2
import pytest
from tablecrow.tables.postgres import database_has_table

from packetraven import APRSDatabaseTable
from packetraven.configuration.credentials import DatabaseCredentials
from packetraven.packets import APRSPacket


@pytest.fixture
def credentials() -> DatabaseCredentials:
    hostname = os.environ['POSTGRES_HOSTNAME']
    database = os.environ['POSTGRES_DATABASE']
    username = os.environ['POSTGRES_USERNAME']
    password = os.environ['POSTGRES_PASSWORD']
    port = os.environ['POSTGRES_PORT']

    return DatabaseCredentials(
        hostname=hostname, database=database, username=username, password=password, port=port,
    )


@pytest.fixture
def connection(credentials) -> psycopg2.connect:
    return psycopg2.connect(
        host=credentials['hostname'],
        port=credentials['port'],
        database=credentials['database'],
        user=credentials['username'],
        password=credentials['password'],
    )


def test_packet_database(connection, credentials):
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
        hostname=credentials['database']['hostname'],
        database=credentials['database']['database'],
        table=table_name,
        username=credentials['database']['username'],
        password=credentials['database']['password'],
        ssh_hostname=credentials['database']['ssh_hostname'],
        ssh_username=credentials['database']['ssh_username'],
        ssh_password=credentials['database']['ssh_password'],
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
