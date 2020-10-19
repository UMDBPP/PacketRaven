import unittest

from packetraven.parsing import InvalidPacketError, parse_raw_aprs


class TestParser(unittest.TestCase):
    def test_parse_aprs_packet(self):
        parsed_packet = parse_raw_aprs(
            'W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu')

        assert parsed_packet['from'] == 'W3EAX-8'
        assert parsed_packet['longitude'] == -77.90921071284187
        assert parsed_packet['latitude'] == 39.7003564996876
        assert parsed_packet['altitude'] == 8201.8632
        assert parsed_packet['comment'] == '|!Q|  /W3EAX,262,0,18\'C,http://www.umd.edu'

    def test_partial_packets(self):
        with self.assertRaises(InvalidPacketError):
            parse_raw_aprs('W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,KM4LKM')

        with self.assertRaises(InvalidPacketError):
            parse_raw_aprs('W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:')


if __name__ == '__main__':
    unittest.main()
