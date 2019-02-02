"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import serial

APRS_PACKET_MINIMUM_LENGTH = 12
RADIO_BAUD_RATE = 19200


def raw_packets_from_serial(port_name: str, baud_rate: int = RADIO_BAUD_RATE, timeout: int = 1) -> list[str]:
    """
    Get potential packet strings from given serial port.

    :param port_name: serial port to radio
    :param baud_rate: baud rate of serial connection
    :param timeout: seconds to wait for serial output
    :return: list of candidate packet strings
    """

    packet_candidates = []

    with serial.Serial(port_name, baudrate=baud_rate, timeout=timeout) as serial_connection:
        # check if serial connection has data in its input buffer
        if serial_connection.in_waiting > 0:
            serial_output = serial_connection.readlines()
            for line in serial_output:
                if len(line) > APRS_PACKET_MINIMUM_LENGTH:
                    packet_candidates.append(line.decode('utf-8'))

    return packet_candidates


if __name__ == '__main__':
    packet_candidates = raw_packets_from_serial('/dev/ttyUSB0')

    print(f'{len(packet_candidates)} packet candidates found')
    print(packet_candidates)
