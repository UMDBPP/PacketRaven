"""
Parse a APRS packets from raw strings.

__authors__ = ['Zachary Burnett', 'Nick Rossomando']
"""

import aprslib


class PartialPacketError(Exception):
    pass


def parse_aprs_packet(raw_aprs: str) -> dict:
    """
    Parse APRS fields from raw packet string.

    APRS format reference: http://www.aprs.org/doc/APRS101.PDF

    :param raw_aprs: raw APRS string
    :return: dictionary of APRS fields
    """

    try:
        parsed_packet = aprslib.parse(raw_aprs)
    except aprslib.ParseError as error:
        raise PartialPacketError(str(error))

    # parsed = {'raw': str(raw_aprs)}
    #
    # if ':' not in raw_aprs:
    #     raise PartialPacketError('location data missing')
    #
    # parsed['from'], raw_aprs = raw_aprs.split('>', 1)
    # parsed['to'], raw_aprs = raw_aprs.split(',', 1)
    # parsed['path'], raw_aprs = raw_aprs.split(':', 1)
    # parsed['path'] = parsed['path'].split(',')
    # parsed['via'] = parsed['path'][-1]
    #
    # parsed['messagecapable'] = raw_aprs[0] in ['!', '/']
    #
    # try:
    #     raw_aprs = raw_aprs[2:]
    #
    #     # TODO add parsing for uncompressed coordinates
    #     lonlat_string = raw_aprs[:8]
    #     parsed['latitude'] = decompress_aprs_lat(lonlat_string[:4])
    #     parsed['longitude'] = decompress_aprs_lon(lonlat_string[4:])
    #     parsed['symbol'] = raw_aprs[8]
    #
    #     raw_aprs = raw_aprs[9:]
    #
    #     # TODO add parsing for more altitude formats
    #     # convert altitude from feet to meters
    #     parsed['altitude'] = int(re.findall('/A=.{6}', raw_aprs)[0][3:]) * 0.3048
    #
    #     parsed['comment'] = re.split('/A=.{6}', raw_aprs)[-1]
    # except IndexError:
    #     raise PartialPacketError('packet terminated unexpectedly')
    #
    # return parsed

    return parsed_packet


def decompress_aprs_lon(compressed_lon: str) -> float:
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


def decompress_aprs_lat(compressed_lat: str) -> float:
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
