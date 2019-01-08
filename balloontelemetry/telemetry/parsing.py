"""
Parse a APRS packets from raw strings.

__authors__ = ['Zachary Burnett']
"""


def parse_aprs_packet(raw_string: str) -> dict:
    """
    Parse APRS fields from raw packet string.

    APRS format reference: http://www.aprs.org/doc/APRS101.PDF

    TODO detect partial packets

    :param raw_string: raw APRS string
    :return: dictionary of APRS fields
    """

    parsed_packet = {}

    return parsed_packet


def decode_lonlat(encoded_lonlat: str) -> float:
    converted_floats = []
    current_power = len(encoded_lonlat) - 1

    for character in encoded_lonlat:
        converted_floats.append(float(ord(character) - 33) * (91 ** current_power))
        current_power -= 1

    return sum(converted_floats)


def convert_lon(compressed_lon: str) -> float:
    return -180 + (decode_lonlat(compressed_lon) / 190463)


def convert_lat(compressed_lat: str) -> float:
    return 90 - (decode_lonlat(compressed_lat) / 380926)


if __name__ == '__main__':
    parsed_packet = parse_aprs_packet(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu")

    print(parsed_packet)
