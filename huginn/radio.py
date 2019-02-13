"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import serial
from serial.tools import list_ports


def find_port() -> str:
    com_ports = serial.tools.list_ports.comports()

    if len(com_ports) > 0:
        return com_ports[0].device
    else:
        return None


def connect(serial_port: str = None) -> serial.Serial:
    """
    Connect to radio over serial port.

    :param serial_port: port name
    :return: serial connection
    """

    if serial_port is None:
        serial_port = find_port()

    if serial_port is None:
        raise EnvironmentError('No open serial ports found.')

    return serial.Serial(serial_port, baudrate=9600, timeout=1)


def get_packets(serial_connection: serial.Serial) -> list:
    """
    Get potential packet strings from given serial connection.

    :param serial_connection: open serial object
    :return: list of APRS strings transmitted from given callsigns
    """

    return [packet.decode('utf-8') for packet in serial_connection.readlines()]


if __name__ == '__main__':
    packet_candidates = get_packets(connect())
    print(packet_candidates)
