"""
Balloon telemetry parsing, display, and logging.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import datetime
import logging
import os
import sys
import time

from huginn import parsing, radio, packets, tracks

if __name__ == '__main__':
    if len(sys.argv) > 1:
        log_filename = sys.argv[1]
    else:
        log_filename = os.path.join(os.path.expanduser('~'), 'Desktop', 'log')

    if len(sys.argv) > 2:
        serial_port = sys.argv[2]
    else:
        serial_port = None

    if len(sys.argv) > 3:
        debug = bool(sys.argv[3])
    else:
        debug = False

    if os.path.isdir(log_filename):
        if not os.path.exists(log_filename):
            os.mkdir(log_filename)
        log_filename = os.path.join(log_filename, f'{datetime.datetime.now().strftime("%Y%m%dT%H%M%S")}_huginn_log.txt')

    with radio.connect(serial_port) as radio_connection:
        log_formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(message)s', '%Y-%m-%d %H:%M:%S')

        log_file = logging.FileHandler(log_filename)
        log_file.setLevel(logging.INFO)
        log_file.setFormatter(log_formatter)

        log_console = logging.StreamHandler()
        log_console.setLevel(logging.DEBUG)
        log_console.setFormatter(log_formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(log_file)
        root_logger.addHandler(log_console)

        packet_tracks = {}

        logging.info(f'Opening {radio_connection.name}.')

        while True:
            raw_packets = radio.read(radio_connection)

            for raw_packet in raw_packets:
                try:
                    parsed_packet = packets.APRSPacket(raw_packet)
                except parsing.PartialPacketError as error:
                    parsed_packet = None
                    logging.debug(f'PartialPacketError: {error} ("{raw_packet}")')

                if parsed_packet is not None:
                    callsign = parsed_packet['callsign']

                    if callsign in packet_tracks:
                        packet_tracks[callsign].append(parsed_packet)
                    else:
                        packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])

                    ascent_rate = packet_tracks[callsign].ascent_rate()
                    ground_speed = packet_tracks[callsign].ground_speed()
                    seconds_to_impact = packet_tracks[callsign].seconds_to_impact()

                    logging.info(
                        f'{parsed_packet} ascent_rate={ascent_rate} ground_speed={ground_speed} seconds_to_impact={seconds_to_impact}')

            time.sleep(1)
