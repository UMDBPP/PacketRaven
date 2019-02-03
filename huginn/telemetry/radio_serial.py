"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import serial

APRS_PACKET_MINIMUM_LENGTH = 12


def raw_packets_from_serial(port_name: str, timeout: int = 1) -> list:
    """
    Get potential packet strings from given serial port.

    :param port_name: serial port to radio
    :param timeout: timeout to wait for radio lines
    :return: list of candidate packet strings
    """

    packet_candidates = []

    with serial.Serial(port_name, timeout=1) as serial_connection:
        lines = serial_connection.readlines()
        for line in lines:
            if len(line) > APRS_PACKET_MINIMUM_LENGTH:
                packet_candidates.append(line.decode('utf-8'))

    return packet_candidates


if __name__ == '__main__':
    # packet_candidates = raw_packets_from_serial('/dev/ttyUSB0')
    packet_candidates = raw_packets_from_serial('COM8')

    print(f'{len(packet_candidates)} packet candidates found')
    print(packet_candidates)
