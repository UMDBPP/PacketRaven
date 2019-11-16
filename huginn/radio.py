"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import logging
from datetime import datetime

from serial import Serial
from serial.tools import list_ports

from huginn.packets import APRSLocationPacket


def ports() -> str:
    """
    Iterate over available serial ports.

    :return: port name
    """

    for com_port in list_ports.comports():
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


def parse_packet(raw_packet: str, packet_time: datetime = None) -> APRSLocationPacket:
    try:
        return APRSLocationPacket(raw_packet, packet_time)
    except Exception as error:
        logging.error(f'{error.__class__.__name__}: {error} for raw packet "{raw_packet}"')


class APRSRadio:
    def __init__(self, serial_port: str = None):
        """
        Connect to radio over given serial port.

        :param serial_port: port name
        """

        if serial_port is None:
            self.serial_port = port()
        else:
            self.serial_port = serial_port.strip('"')

        self.is_text_file = self.serial_port is not None and '.txt' in self.serial_port

        if self.is_text_file:
            # open text file as dummy serial connection
            self.serial_connection = open(self.serial_port)
        else:
            self.serial_connection = Serial(self.serial_port, baudrate=9600, timeout=1)

    @property
    def packets(self) -> [APRSLocationPacket]:
        """
        Get potential packet strings from given serial connection.

        :return: list of APRS strings transmitted from given callsigns
        """

        parsed_packets = []

        if self.is_text_file:
            line = self.serial_connection.readline()
            if len(line) > 0:
                packet_time = datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
                raw_packet = str(line[25:]).strip('\n')
                parsed_packets.append(parse_packet(raw_packet, packet_time))
        else:
            for line in self.serial_connection.readlines():
                parsed_packets.append(parse_packet(line.decode('utf-8')))

        return parsed_packets

    def close(self):
        self.serial_connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.serial_port}, r"{self.is_text_file}")'


if __name__ == '__main__':
    packet_candidates = APRSRadio().packets
    print(packet_candidates)
