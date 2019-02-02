"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import serial

APRS_PACKET_MINIMUM_LENGTH = 12


def raw_packets_from_serial(port_name: str, max_lines: int = 10) -> list:
    """
    Get potential packet strings from given serial port.

    :param port_name: serial port to radio
    :param max_lines: maximum number of lines to extract
    :return: list of candidate packet strings
    """

    packet_candidates = []

    with serial.Serial(port_name) as serial_connection:
        # check if serial connection has data in its input buffer
        if serial_connection.in_waiting > 0:
            num_lines = 0

            while num_lines <= max_lines:
                line = serial_connection.readline()
                num_lines += 1

                if len(line) > APRS_PACKET_MINIMUM_LENGTH:
                    packet_candidates.append(line.decode('utf-8'))

    return packet_candidates


if __name__ == '__main__':
    packet_candidates = raw_packets_from_serial('/dev/ttyUSB0')

    print(f'{len(packet_candidates)} packet candidates found')
    print(packet_candidates)
