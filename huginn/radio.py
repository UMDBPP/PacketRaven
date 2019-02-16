"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import serial
from serial.tools import list_ports


def ports() -> str:
    """
    Iterate over available serial ports.

    :return: port name
    """

    com_ports = serial.tools.list_ports.comports()

    for com_port in com_ports:
        yield com_port.device
    else:
        return None


def port() -> str:
    """
    Get next port in ports list.

    :return: port name
    """

    try:
        return next(ports())
    except StopIteration:
        raise OSError('No open serial ports.')


def connect(serial_port: str = None) -> serial.Serial:
    """
    Connect to radio over given serial port.

    :param serial_port: port name
    :return: serial connection
    """

    if serial_port is None:
        serial_port = port()

    return serial.Serial(serial_port, baudrate=9600, timeout=1)


def read(serial_connection: serial.Serial) -> list:
    """
    Get potential packet strings from given serial connection.

    :param serial_connection: open serial object
    :return: list of APRS strings transmitted from given callsigns
    """

    return [packet.decode('utf-8') for packet in serial_connection.readlines()]


if __name__ == '__main__':
    packet_candidates = read(connect())
    print(packet_candidates)
