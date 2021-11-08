from abc import ABC
from datetime import datetime

from kiss import KISS
from serial import Serial

from packetraven.connections.base import (
    APRSPacketSource,
    LOGGER,
    next_open_serial_port,
    TimeIntervalError,
)
from packetraven.packets import APRSPacket
from packetraven.packets.parsing import InvalidPacketError


class SerialAPRSConnection(APRSPacketSource, ABC):
    def __init__(self, serial_port: str = None, callsigns: [str] = None, baudrate: int = None):
        """
        Connect to a given serial port.

        :param serial_port: port name
        :param callsigns: list of callsigns to return from source
        :param baudrate: baud rate of serial communication
        """

        if baudrate is None:
            baudrate = 9600

        if serial_port is None or serial_port == '' or serial_port == 'auto':
            try:
                serial_port = next_open_serial_port()
            except ConnectionError:
                raise ConnectionError('could not find TNC connected to serial')
        else:
            serial_port = serial_port.strip('"')

        super().__init__(serial_port, callsigns)

        self.__baudrate = baudrate

    @property
    def baudrate(self) -> int:
        return self.__baudrate


class SerialTNC(SerialAPRSConnection):
    def __init__(self, serial_port: str = None, callsigns: [str] = None, baudrate: int = None):
        super().__init__(serial_port, callsigns, baudrate)
        self.serial_connection = Serial(port=self.location, baudrate=self.baudrate, timeout=1)
        self.__last_access_time = None

    @property
    def packets(self) -> [APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )
        packets = []
        for line in self.serial_connection.readlines():
            try:
                packet = APRSPacket.from_frame(line, source=self.location)
                packets.append(packet)
            except Exception as error:
                LOGGER.error(f'{error.__class__.__name__} - {error}')
        if self.callsigns is not None:
            packets = [packet for packet in packets if packet.from_callsign in self.callsigns]
        self.__last_access_time = datetime.now()
        return packets

    def close(self):
        self.serial_connection.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.location)}, {repr(self.callsigns)})'


class SerialKISS(APRSPacketSource):
    def __init__(self, serial_port: str = None, callsigns: [str] = None, baudrate: int = None):
        super().__init__(serial_port, callsigns, baudrate)
        self.serial_connection = KISS(port=self.location, speed=self.baudrate, timeout=1)
        self.__last_access_time = None

    @property
    def packets(self) -> [APRSPacket]:
        if self.__last_access_time is not None and self.interval is not None:
            interval = datetime.now() - self.__last_access_time
            if interval < self.interval:
                raise TimeIntervalError(
                    f'interval {interval} less than minimum interval {self.interval}'
                )

        packets = []

        def add_frames(frame: str):
            try:
                packet = APRSPacket.from_frame(frame)
                if self.callsigns is not None:
                    if packet.from_callsign in self.callsigns:
                        if packet not in packets:
                            packets.append(packet)
            except InvalidPacketError:
                pass

        self.serial_connection.start()
        self.serial_connection.read(callback=add_frames, readmode=False)

        self.__last_access_time = datetime.now()
        return packets

    def close(self):
        self.serial_connection.stop()

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.location)}, {repr(self.callsigns)})'
