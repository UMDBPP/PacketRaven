"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import serial

APRS_PACKET_MINIMUM_LENGTH = 12
RADIO_BAUD_RATE = 1200


def serial_packet_candidates(port_name: str, baud_rate: int = RADIO_BAUD_RATE, timeout: int = 1) -> list:
    """
    Get potential packet strings from given serial port.

    :param port_name: serial port to radio
    :param baud_rate: baud rate to read serial
    :param timeout: timeout to wait for radio lines
    :return: list of candidate packet strings
    """

    packet_candidates = []

    with serial.Serial(port_name, baudrate=baud_rate, timeout=timeout) as serial_connection:
        lines = serial_connection.readlines()
        for line in lines:
            if len(line) > APRS_PACKET_MINIMUM_LENGTH:
                packet_candidates.append(line.decode('utf-8'))

    return packet_candidates


if __name__ == '__main__':
    import os

    if os.name is 'nt':
        serial_port = 'COM0'
    else:
        serial_port = '/dev/ttyUSB0'

    packet_candidates = serial_packet_candidates(serial_port)

    print(f'{len(packet_candidates)} packet candidates found')
    print(packet_candidates)
