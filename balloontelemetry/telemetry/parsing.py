"""
Parse a APRS packets from raw strings.

__authors__ = ['Zachary Burnett', 'Nick Rossomando']
"""


def parse_aprs_packet(raw_aprs: str) -> dict:
    """
    Parse APRS fields from raw packet string.

    APRS format reference: http://www.aprs.org/doc/APRS101.PDF

    TODO detect partial packets

    :param raw_aprs: raw APRS string
    :return: dictionary of APRS fields
    """

    parsed = {'raw': raw_aprs}

    working_string = str(raw_aprs)

    parsed['from'], working_string = working_string.split('>', 1)
    parsed['to'], working_string = working_string.split(',', 1)

    parsed['path'] = working_string.split(',')
    parsed['path'][-1], working_string = parsed['path'][-1].split(':', 1)
    parsed['via'] = parsed['path'][-1]

    parsed['messagecapable'] = working_string[0] in ['!', '/']

    working_string = working_string[2:]

    lonlat, working_string = working_string.split('/A=', 1)

    return parsed


def decompress_lon(compressed_lon: str) -> float:
    """
    Decode longitude string from base 91 ASCII to float.

    :param compressed_lon: compressed longitude string
    :return: longitude
    """

    converted_floats = []
    current_power = len(compressed_lon) - 1

    for character in compressed_lon:
        converted_floats.append(float(ord(character) - 33) * (91 ** current_power))
        current_power -= 1

    return -180 + (sum(converted_floats) / 190463)


def decompress_lat(compressed_lat: str) -> float:
    """
    Decode latitude string from base 91 ASCII to float.

    :param compressed_lat: compressed latitude string
    :return: latitude
    """

    converted_floats = []
    current_power = len(compressed_lat) - 1

    for character in compressed_lat:
        converted_floats.append(float(ord(character) - 33) * (91 ** current_power))
        current_power -= 1

    return 90 - (sum(converted_floats) / 380926)


if __name__ == '__main__':
    parsed_packet = parse_aprs_packet(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu")

    print(parsed_packet)
