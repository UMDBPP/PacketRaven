from abc import ABC, abstractmethod
from datetime import timedelta
from socket import socket
from typing import Union

import requests
from serial.tools import list_ports

from packetraven.packets import APRSPacket, LocationPacket


class Connection(ABC):
    interval: timedelta = None

    def __init__(self, location: str):
        self.location = location

    @abstractmethod
    def close(self):
        raise NotImplementedError


class NetworkConnection(Connection):
    @property
    def connected(self) -> bool:
        """ whether current session has a network connection """
        try:
            requests.get(self.location, timeout=2)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False


class PacketSource(Connection):
    @property
    @abstractmethod
    def packets(self) -> [LocationPacket]:
        """
        most recent available location packets, since the last minimum time interval if applicable

        :return: list of location packets
        """

        raise NotImplementedError


class APRSPacketSource(PacketSource):
    def __init__(self, location: str, callsigns: [str]):
        """
        Create a new generic APRS packet connection.

        :param location: location of APRS packets
        :param callsigns: list of callsigns to return from source
        """

        super().__init__(location)
        self.callsigns = callsigns

    @property
    @abstractmethod
    def packets(self) -> [APRSPacket]:
        """ most recent available APRS packets, since the last minimum time interval (if applicable) """
        raise NotImplementedError


class PacketSink(Connection):
    @property
    @abstractmethod
    def send(self, packets: [LocationPacket]):
        """ send given packets to remote """
        raise NotImplementedError


class APRSPacketSink(PacketSink):
    @property
    def send(self, packets: [APRSPacket]):
        super().send(packets)


def random_open_tcp_port() -> int:
    open_socket = socket()
    open_socket.bind(('', 0))
    return open_socket.getsockname()[1]


def next_open_serial_port() -> str:
    """
    Get next port in ports list.

    :return: port name
    """

    try:
        return next(available_serial_ports())
    except StopIteration:
        raise ConnectionError('no open serial ports')


def available_serial_ports() -> str:
    """
    Iterate over available serial ports.

    :return: port name
    """

    for com_port in list_ports.comports():
        yield com_port.device
    else:
        return None


def split_URL_port(url: str) -> (str, Union[str, None]):
    """
    Split the given URL into host and port, assuming port is appended after a colon.

    :param url: URL string
    :return: URL and port (if found)
    """

    port = None

    if url.count(':') > 0:
        url = url.split(':')
        if 'http' in url:
            url = ':'.join(url[:2])
            if len(url) > 2:
                port = int(url[2])
        else:
            url, port = url
            port = int(port)

    return url, port
