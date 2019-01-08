"""
Parse a APRS packets from raw strings.

__authors__ = ['Zachary Burnett']
"""


def parse_aprs_packet(raw_string: str) -> dict:
    """
    Parses APRS fields from packet

    APRS packet reference: http://www.aprs.org/doc/APRS101.PDF

    TODO detect partial packets

    :param raw_string: raw APRS string
    :return: dictionary of APRS fields
    """

    raw_string.split()

    return {}


if __name__ == '__main__':
    parsed_packet = parse_aprs_packet(
        "W3EAX-8>APRS,WIDE1-1,WIDE2-1,qAR,K3DO-11:!/:Gh=:j)#O   /A=026909|!Q|  /W3EAX,262,0,18'C,http://www.umd.edu")

    print(parsed_packet)
