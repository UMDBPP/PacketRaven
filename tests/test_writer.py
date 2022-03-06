from datetime import datetime

import pytest
import pytz

from packetraven.packets import APRSPacket
from packetraven.packets.tracks import APRSTrack, LocationPacketTrack
from packetraven.packets.writer import write_packet_tracks
from tests import OUTPUT_DIRECTORY, REFERENCE_DIRECTORY, check_reference_directory


@pytest.fixture
def packet_track():
    return APRSTrack(
        packets=[
            APRSPacket.from_frame(
                "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
                packet_time=pytz.timezone('America/New_York').localize(
                    datetime(2018, 11, 11, 10, 20, 13)
                ),
            ),
            APRSPacket.from_frame(
                "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,"
                'http://www.umd.edu',
                packet_time=pytz.timezone('America/New_York').localize(
                    datetime(2018, 11, 11, 10, 21, 24)
                ),
            ),
            APRSPacket.from_frame(
                "W3EAX-8>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,"
                'nearspace.umd.edu',
                packet_time=pytz.timezone('America/New_York').localize(
                    datetime(2019, 2, 3, 14, 39, 28)
                ),
            ),
        ],
        callsign='W3EAX-8',
    )


def test_write_kml(packet_track):
    reference_directory = REFERENCE_DIRECTORY / 'test_write_kml'
    output_directory = OUTPUT_DIRECTORY / 'test_write_kml'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    write_packet_tracks([packet_track], output_directory / 'tracks.kml')
    check_reference_directory(output_directory, reference_directory)


def test_write_geojson(packet_track):
    reference_directory = REFERENCE_DIRECTORY / 'test_write_geojson'
    output_directory = OUTPUT_DIRECTORY / 'test_write_geojson'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    write_packet_tracks([packet_track], output_directory / 'tracks.geojson')
    check_reference_directory(output_directory, reference_directory)


def test_read_geojson():
    reference_directory = REFERENCE_DIRECTORY / 'test_write_geojson'

    tracks = LocationPacketTrack.from_file(reference_directory / 'tracks.geojson')
    aprs_tracks = APRSTrack.from_file(reference_directory / 'tracks.geojson')

    assert tracks[0].attributes['callsign'] == 'W3EAX-8'
    assert aprs_tracks[0].callsign == 'W3EAX-8'


def test_write_txt(packet_track):
    reference_directory = REFERENCE_DIRECTORY / 'test_write_txt'
    output_directory = OUTPUT_DIRECTORY / 'test_write_txt'

    if not output_directory.exists():
        output_directory.mkdir(parents=True, exist_ok=True)

    write_packet_tracks([packet_track], output_directory / 'tracks.txt')
    check_reference_directory(output_directory, reference_directory)
