from abc import ABC, abstractmethod
from datetime import timedelta

import requests
from serial.tools import list_ports

from packetraven.packets import APRSPacket, LocationPacket
from packetraven.utilities import get_logger, repository_root

LOGGER = get_logger('connection')

CREDENTIALS_FILENAME = repository_root() / 'credentials.config'


class TimeIntervalError(Exception):
    pass


class Connection(ABC):
    interval: timedelta = None

    def __init__(self, location: str):
        self.location = location

    @abstractmethod
    def close(self):
        raise NotImplementedError


class NetworkConnection(Connection):
    """
    A connection over the Internet
    """

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
