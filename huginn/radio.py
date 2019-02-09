"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import serial
from serial.tools import list_ports


def connect(serial_port: str = None) -> serial.Serial:
    """
    Connect to radio over serial port.

    :param serial_port: port name
    :return: serial connection
    """

    if serial_port is None:
        com_ports = serial.tools.list_ports.comports()

        if len(com_ports) == 0:
            raise EnvironmentError('No open serial ports found.')

        serial_port = com_ports[0].device

    return serial.Serial(serial_port, baudrate=9600, timeout=1)


def packets(serial_connection: serial.Serial) -> list:
    """
    Get potential packet strings from given serial connection.

    :param serial_connection: open serial object
    :return: list of APRS strings transmitted from given callsigns
    """

    return [packet.decode('utf-8') for packet in serial_connection.readlines()]


if __name__ == '__main__':
    packet_candidates = packets(connect())
    print(packet_candidates)
