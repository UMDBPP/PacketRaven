from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from packetraven.packets import APRSLocationPacket
from packetraven.tracks import APRSTrack
from packetraven.writer import write_aprs_packet_tracks


class TestWriter(unittest.TestCase):
    def test_write_kml(self):
        packet_1 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,"
            "http://www.umd.edu",
            time=datetime(2018, 11, 11, 10, 21, 24))
        packet_3 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,"
            "nearspace.umd.edu",
            time=datetime(2019, 2, 3, 14, 39, 28))

        track = APRSTrack('W3EAX-13', [packet_1, packet_2, packet_3])

        with TemporaryDirectory() as temporary_directory:
            output_filename = Path(temporary_directory) / 'test_output.kml'
            write_aprs_packet_tracks([track], output_filename)
            assert output_filename.exists()

    def test_write_geojson(self):
        packet_1 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu",
            time=datetime(2018, 11, 11, 10, 20, 13))
        packet_2 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-8>APRS,N3TJJ-12,WIDE1*,WIDE2-1,qAR,N3FYI-2:!/:GiD:jcwO   /A=028365|!R|  /W3EAX,267,0,18'C,"
            "http://www.umd.edu",
            time=datetime(2018, 11, 11, 10, 21, 24))
        packet_3 = APRSLocationPacket.from_raw_aprs(
            "W3EAX-13>APRS,KC3FIT-1,WIDE1*,WIDE2-1,qAR,KC3AWP-10:!/:JL2:u4wO   /A=043080|!j|  /W3EAX,326,0,20'C,"
            "nearspace.umd.edu",
            time=datetime(2019, 2, 3, 14, 39, 28))

        track = APRSTrack('W3EAX-13', [packet_1, packet_2, packet_3])

        with TemporaryDirectory() as temporary_directory:
            output_filename = Path(temporary_directory) / 'test_output.geojson'
            write_aprs_packet_tracks([track], output_filename)
            assert output_filename.exists()


if __name__ == '__main__':
    unittest.main()
