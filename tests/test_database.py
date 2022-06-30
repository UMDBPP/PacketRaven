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
    hostname = os.environ.get("POSTGRES_HOSTNAME")
    database = os.environ.get("POSTGRES_DATABASE")
    username = os.environ.get("POSTGRES_USERNAME")
    password = os.environ.get("POSTGRES_PASSWORD")
    port = os.environ.get("POSTGRES_PORT")

    return DatabaseCredentials(
        hostname=hostname,
        database=database,
        username=username,
        password=password,
        port=port,
    )


@pytest.fixture
def connection(credentials) -> psycopg2.connect:
    return psycopg2.connect(
        host=credentials["hostname"],
        port=credentials["port"],
        database=credentials["database"],
        user=credentials["username"],
        password=credentials["password"],
    )


@pytest.mark.skipif(
    "POSTGRES_HOSTNAME" not in os.environ,
    reason="no environment variables set for connection information",
)
def test_packet_database(connection, credentials):
    table_name = "test_table"

    packet_1 = APRSPacket.from_frame(
        "W3EAX-13>APRS,N3KTX-10*,WIDE1,WIDE2-1,qAR,N3TJJ-11:!/:J..:sh'O   "
        "/A=053614|!g|  /W3EAX,313,0,21'C,nearspace.umd.edu",
        packet_time=datetime(2019, 2, 3, 14, 36, 16),
    )
    packet_2 = APRSPacket.from_frame(
        "W3EAX-13>APRS,WIDE1-1,WIDE2-1,qAR,W4TTU:!/:JAe:tn8O   "
        "/A=046255|!i|  /W3EAX,322,0,20'C,nearspace.umd.edu",
        packet_time=datetime(2019, 2, 3, 14, 38, 23),
    )
    packet_3 = APRSPacket.from_frame(
        "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   "
        "/A=043080|!j|  /W3EAX,326,0,20'C,nearspace.umd.edu",
        packet_time=datetime(2019, 2, 3, 14, 39, 28),
    )

    input_packets = [packet_1, packet_2, packet_3]

    with connection:
        with connection.cursor() as cursor:
            if database_has_table(cursor, table_name):
                cursor.execute(f"DROP TABLE {table_name};")

    ssh_kwargs = {}
    if credentials["tunnel"] is not None:
        ssh_kwargs["hostname"] = (credentials["tunnel"]["hostname"],)
        ssh_kwargs["username"] = (credentials["tunnel"]["username"],)
        ssh_kwargs["password"] = (credentials["tunnel"]["password"],)

    packet_table = APRSDatabaseTable(
        hostname=credentials["hostname"],
        database=credentials["database"],
        table=table_name,
        username=credentials["username"],
        password=credentials["password"],
        **ssh_kwargs,
    )
    packet_table.insert(input_packets)

    assert packet_1 == packet_table[packet_1.time, packet_1.from_callsign]

    packets = packet_table.packets

    with connection:
        with connection.cursor() as cursor:
            assert database_has_table(cursor, table_name)
            cursor.execute(f"DROP TABLE {table_name};")

    assert len(packets) > 0 and all(
        packets[packet_index] == input_packets[packet_index]
        for packet_index in range(len(packets))
    )
