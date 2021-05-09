from typing import Union

import aprslib


def parse_raw_aprs(raw_aprs: Union[str, dict]) -> dict:
    """
    Parse APRS fields from raw packet string.

    APRS format reference: http://www.aprs.org/doc/APRS101.PDF

    :param raw_aprs: raw APRS string
    :return: dictionary of APRS fields
    """

    if not isinstance(raw_aprs, dict):
        try:
            parsed_packet = aprslib.parse(raw_aprs)
        except aprslib.ParseError as error:
            raise InvalidPacketError(str(error))
    else:
        parsed_packet = {
            'from': raw_aprs['srccall'],
            'to': raw_aprs['dstcall'],
            'path': raw_aprs['path'].split(','),
            'timestamp': raw_aprs['time'],
            'symbol': raw_aprs['symbol'][1:],
            'symbol_table': raw_aprs['symbol'][0],
            'latitude': float(raw_aprs['lat']),
            'longitude': float(raw_aprs['lng']),
            'altitude': float(raw_aprs['altitude']) if 'altitude' in raw_aprs else None,
            'comment': raw_aprs['comment'] if 'comment' in raw_aprs else 'comment',
        }

    # parsed_packet = {'raw': str(raw_aprs)}
    #
    # if ':' not in raw_aprs:
    #     raise InvalidPacketError('location data missing')
    #
    # parsed_packet['from'], raw_aprs = raw_aprs.split('>', 1)
    # parsed_packet['to'], raw_aprs = raw_aprs.split(',', 1)
    # parsed_packet['path'], raw_aprs = raw_aprs.split(':', 1)
    # parsed_packet['path'] = parsed_packet['path'].split(',')
    # parsed_packet['via'] = parsed_packet['path'][-1]
    #
    # parsed_packet['messagecapable'] = raw_aprs[0] in ['!', '/']
    #
    # try:
    #     raw_aprs = raw_aprs[2:]
    #
    #     # TODO add parsing for uncompressed coordinates
    #     lonlat_string = raw_aprs[:8]
    #     parsed_packet['latitude'] = decompress_latitude(lonlat_string[:4])
    #     parsed_packet['longitude'] = decompress_longitude(lonlat_string[4:])
    #     parsed_packet['symbol'] = raw_aprs[8]
    #
    #     raw_aprs = raw_aprs[9:]
    #
    #     # TODO add parsing for more altitude formats
    #     # convert altitude from feet to meters
    #     parsed_packet['altitude'] = int(re.findall('/A=.{6}', raw_aprs)[0][3:]) * 0.3048
    #
    #     parsed_packet['comment'] = re.split('/A=.{6}', raw_aprs)[-1]
    # except IndexError:
    #     raise InvalidPacketError('packet terminated unexpectedly')

    return parsed_packet


class InvalidPacketError(Exception):
    pass


def decompress_longitude(compressed_longitude: str) -> float:
    """
    Decode longitude string from APRS compressed format (shifted ASCII in model.py 91) to a float.

    :param compressed_longitude: compressed APRS longitude string
    :return: longitude
    """

    converted_floats = []
    current_power = len(compressed_longitude) - 1

    for character in compressed_longitude:
        converted_floats.append(float(ord(character) - 33) * (91 ** current_power))
        current_power -= 1

    return -180 + (sum(converted_floats) / 190463)


def decompress_latitude(compressed_latitude: str) -> float:
    """
    Decode latitude string from APRS compressed format (shifted ASCII in model.py 91) to a float.

    :param compressed_latitude: compressed APRS latitude string
    :return: latitude
    """

    converted_floats = []
    current_power = len(compressed_latitude) - 1

    for character in compressed_latitude:
        converted_floats.append(float(ord(character) - 33) * (91 ** current_power))
        current_power -= 1

    return 90 - (sum(converted_floats) / 380926)
