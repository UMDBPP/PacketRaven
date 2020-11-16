from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytz

from packetraven.packets import APRSPacket
from packetraven.tracks import APRSTrack
from packetraven.utilities import repository_root
from packetraven.writer import write_aprs_packet_tracks

REFERENCE_DIRECTORY = repository_root() / 'tests' / 'reference'

PACKET_TRACK = APRSTrack(
    'W3EAX-13',
    [
        APRSPacket.from_frame(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            packet_time=pytz.timezone("America/New_York").localize(datetime(2018, 11, 11, 10, 20, 13)),
        ),
        APRSPacket.from_frame(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,"
            'http://www.umd.edu',
            packet_time=pytz.timezone("America/New_York").localize(datetime(2018, 11, 11, 10, 21, 24)),
        ),
        APRSPacket.from_frame(
            "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,"
            'nearspace.umd.edu',
            packet_time=pytz.timezone("America/New_York").localize(datetime(2019, 2, 3, 14, 39, 28)),
        ),
    ],
)


def test_write_kml():
    filename = 'test_output.kml'
    reference_filename = REFERENCE_DIRECTORY / filename
    with TemporaryDirectory() as temporary_directory:
        output_filename = Path(temporary_directory) / filename
        write_aprs_packet_tracks([PACKET_TRACK], output_filename)
        with open(output_filename) as output_file, open(reference_filename) as reference_file:
            assert output_file.read() == reference_file.read()


def test_write_geojson():
    filename = 'test_output.geojson'
    reference_filename = REFERENCE_DIRECTORY / filename
    with TemporaryDirectory() as temporary_directory:
        output_filename = Path(temporary_directory) / filename
        write_aprs_packet_tracks([PACKET_TRACK], output_filename)
        with open(output_filename) as output_file, open(reference_filename) as reference_file:
            assert output_file.read() == reference_file.read()


def test_write_txt():
    filename = 'test_output.txt'
    reference_filename = REFERENCE_DIRECTORY / filename
    with TemporaryDirectory() as temporary_directory:
        output_filename = Path(temporary_directory) / filename
        write_aprs_packet_tracks([PACKET_TRACK], output_filename)
        with open(output_filename) as output_file, open(reference_filename) as reference_file:
            assert output_file.read() == reference_file.read()
