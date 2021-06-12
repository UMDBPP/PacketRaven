from datetime import datetime

from serial import Serial

from packetraven.connections.base import (
    APRSPacketSource,
    LOGGER,
    next_open_serial_port,
    TimeIntervalError,
)
from packetraven.packets import APRSPacket


class SerialTNC(APRSPacketSource):
    def __init__(self, serial_port: str = None, callsigns: [str] = None):
        """
        Connect to TNC over given serial port.

        :param serial_port: port name
        :param callsigns: list of callsigns to return from source
        """

        if serial_port is None or serial_port == '' or serial_port == 'auto':
            try:
                serial_port = next_open_serial_port()
            except ConnectionError:
                raise ConnectionError('could not find TNC connected to serial')
        else:
            serial_port = serial_port.strip('"')

        self.serial_connection = Serial(serial_port, baudrate=9600, timeout=1)
        super().__init__(self.serial_connection.port, callsigns)
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
