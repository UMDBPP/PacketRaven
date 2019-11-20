"""
Read serial connection from radio and extract APRS packets.

__authors__ = []
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union

import requests
from serial import Serial
from serial.tools import list_ports

from huginn.packets import APRSLocationPacket

APRS_FI_API_FILENAME = 'secret.txt'


class APRSConnection(ABC):
    address: str

    @property
    @abstractmethod
    def packets(self) -> [APRSLocationPacket]:
        """
        List the most recent packets available from this connection.

        :return: list of APRS packets
        """

        raise NotImplementedError

    @abstractmethod
    def __enter__(self):
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError


class Radio(APRSConnection):
    def __init__(self, serial_port: str = None):
        """
        Connect to radio over given serial port.

        :param serial_port: port name
        """

        if serial_port is None:
            try:
                self.serial_port = port()
            except ConnectionError:
                raise ConnectionError('could not find radio over serial connection')
        else:
            self.serial_port = serial_port.strip('"')

        self.serial_connection = Serial(self.serial_port, baudrate=9600, timeout=1)

    @property
    def packets(self) -> [APRSLocationPacket]:
        return [parse_packet(line) for line in self.serial_connection.readlines()]

    def __enter__(self):
        return self.serial_connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.serial_connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.serial_port}")'


class TextFile(APRSConnection):
    def __init__(self, filename: str = None):
        """
        Read APRS packets from a given text file.

        :param filename: path to text file, where each line consists of the time sent (`%Y-%m-%d %H:%M:%S`) followed by the raw APRS string
        """

        self.filename = filename.strip('"')

        # open text file as dummy serial connection
        self.file = open(self.filename)

    @property
    def packets(self) -> [APRSLocationPacket]:
        return [parse_packet(line[25:].strip('\n'), datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S'))
                for line in self.file.readlines() if len(line) > 0]

    def __enter__(self):
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.file.close()

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.filename}")'


class APRS_fi(APRSConnection):
    api_url = 'https://api.aprs.fi/api/get'

    def __init__(self, callsigns: [str], api_key: str = None):
        """
        Connect to https://aprs.fi over given serial port.

        :param callsigns: list of callsigns to watch
        :param api_key: API key for aprs.fi
        """

        if api_key is None:
            with open(APRS_FI_API_FILENAME) as secret_file:
                api_key = secret_file.read().strip()

        self.callsigns = callsigns
        self.api_key = api_key

        if not self.has_network_connection():
            raise ConnectionError(f'No network connection.')

    @property
    def packets(self) -> [APRSLocationPacket]:
        query = f'{self.api_url}?name={",".join(self.callsigns)}&what=loc&apikey={self.api_key}&format=json'

        response = requests.get(query).json()
        if response['result'] != 'fail':
            packets = [parse_packet(packet_candidate) for packet_candidate in response['entries']]
        else:
            logging.warning(f'query failure "{response["code"]}: {response["description"]}"')
            packets = []

        return packets

    def has_network_connection(self) -> bool:
        """
        test network connection

        :return: whether current session has a network connection to APRS API
        """

        try:
            requests.get(self.api_url, timeout=2)
            return True
        except ConnectionError:
            return False

    def __enter__(self):
        if not self.has_network_connection():
            raise ConnectionError(f'No network connection.')

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass

    def __repr__(self):
        callsigns_string = ','.join(f'"{callsign}"' for callsign in self.callsigns)
        return f'{self.__class__.__name__}([{callsigns_string}], r"{self.api_key}")'


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
        raise ConnectionError('No open serial ports.')


def parse_packet(raw_packet: Union[str, bytes, dict], packet_time: datetime = None) -> APRSLocationPacket:
    try:
        return APRSLocationPacket(raw_packet, packet_time)
    except Exception as error:
        logging.error(f'{error.__class__.__name__}: {error} for raw packet "{raw_packet}"')


if __name__ == '__main__':
    BALLOON_CALLSIGNS = ['W3EAX-10', 'W3EAX-11', 'W3EAX-14']

    with open('../secret.txt') as secret_file:
        api_key = secret_file.read().strip()

    aprs_api = APRS_fi(BALLOON_CALLSIGNS, api_key)

    with aprs_api:
        packet_candidates = aprs_api.packets

    print(packet_candidates)
