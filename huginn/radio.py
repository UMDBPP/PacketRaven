"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import datetime
import logging
from typing import List

import serial
from serial.tools import list_ports

from huginn import packets, parsing
from huginn.packets import APRSLocationPacket


def ports() -> str:
    """
    Iterate over available serial ports.

    :return: port name
    """

    for com_port in serial.tools.list_ports.comports():
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


def parse_packet(raw_packet: str, packet_time: datetime.datetime = None) -> APRSLocationPacket:
    try:
        return packets.APRSLocationPacket(raw_packet, packet_time)
    except parsing.PartialPacketError as error:
        logging.debug(f'PartialPacketError: {error} "{raw_packet}"')
    except ValueError as error:
        logging.debug(f'ValueError: {error} "{raw_packet}"')


class Radio:
    def __init__(self, serial_port: str = None):
        """
        Connect to radio over given serial port.

        :param serial_port: port name
        """

        self.serial_port = serial_port
        self.dummy = False

        if self.serial_port is not None and '.txt' in self.serial_port:
            # open text file as dummy serial connection
            self.serial_connection = open(self.serial_port)
            self.dummy = True
        else:
            if self.serial_port is None:
                self.serial_port = port()

            self.serial_connection = serial.Serial(self.serial_port, baudrate=9600, timeout=1)

    def read(self) -> List[APRSLocationPacket]:
        """
        Get potential packet strings from given serial connection.

        :param serial_connection: open serial object
        :return: list of APRS strings transmitted from given callsigns
        """

        parsed_packets = []

        if self.dummy:
            line = self.serial_connection.readline()
            if len(line) > 0:
                packet_time = datetime.datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
                raw_packet = str(line[25:])
                parse_packet(raw_packet, packet_time)
        else:
            for line in self.serial_connection.readlines():
                parse_packet(line.decode('utf-8'))

        return parsed_packets

    def close(self):
        self.serial_connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.serial_port}, r"{self.dummy}")'


if __name__ == '__main__':
    packet_candidates = Radio().read()
    print(packet_candidates)
