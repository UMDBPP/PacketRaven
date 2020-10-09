from abc import ABC, abstractmethod
from socket import socket
from typing import Union

import requests
from serial.tools import list_ports


class Connection(ABC):
    def __init__(self, location: str):
        self.location = location

    @abstractmethod
    def __enter__(self):
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError


class NetworkConnection(Connection):
    def __init__(self, location: str):
        super().__init__(location)

    @property
    def connected(self) -> bool:
        """ whether current session has a network connection """
        try:
            requests.get(self.location, timeout=2)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False


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

    Parameters
    ----------
    url
        URL string

    Returns
    ----------
    str, Union[str, None]
        URL and port (if found)
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
