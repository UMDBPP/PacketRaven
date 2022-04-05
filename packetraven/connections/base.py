from abc import ABC, abstractmethod
from datetime import timedelta
from typing import List

import requests
from serial.tools import list_ports

from packetraven.packets import APRSPacket, LocationPacket


class TimeIntervalError(Exception):
    pass


class Connection(ABC):
    """
    abstraction of a generic connection
    """

    interval: timedelta = None

    def __init__(self, location: str):
        self.location = location
        self.__logger = None

    @abstractmethod
    def close(self):
        raise NotImplementedError


class NetworkConnection(Connection, ABC):
    """
    abstraction of a generic Internet connection
    """

    @property
    def connected(self) -> bool:
        """ whether current session has a network connection """
        try:
            requests.get(self.location, timeout=2)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False


class PacketSource(Connection, ABC):
    """
    abstraction of a connection that can retrieve packets
    """

    def __init__(self, location: str, callsigns: [str] = None):
        if callsigns is not None and len(callsigns) == 0:
            callsigns = None
        self.callsigns = callsigns
        super().__init__(location)

    @property
    @abstractmethod
    def packets(self) -> List[LocationPacket]:
        """
        most recent available location packets, since the last minimum time interval if applicable

        :return: list of location packets
        """

        raise NotImplementedError


class APRSPacketSource(PacketSource):
    def __init__(self, location: str, callsigns: List[str]):
        """
        :param location: location of APRS packets
        :param callsigns: list of callsigns to return from source
        """

        super().__init__(location, callsigns)

    @property
    @abstractmethod
    def packets(self) -> List[APRSPacket]:
        """ most recent available APRS packets, since the last minimum time interval (if applicable) """
        raise NotImplementedError


class PacketSink(Connection):
    """
    abstraction of a connection that can receive packets (upload)
    """

    @property
    @abstractmethod
    def send(self, packets: List[LocationPacket]):
        """ send given packets to remote """
        raise NotImplementedError


class APRSPacketSink(PacketSink):
    @property
    def send(self, packets: List[APRSPacket]):
        super().send(packets)


def next_open_serial_port() -> str:
    """
    get next port in ports list

    :return: port name
    """

    try:
        return next(available_serial_ports())
    except StopIteration:
        raise ConnectionError('no open serial ports')


def available_serial_ports() -> str:
    """
    iterate over available serial ports

    :return: port name
    """

    for com_port in list_ports.comports():
        yield com_port.device
    else:
        return None
