"""
Balloon telemetry parsing, display, and logging.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import datetime
import os
import re
import sys
import time

import logbook

from huginn import parsing, radio, packets, tracks

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        callsigns = sys.argv[1]
    else:
        callsigns = ['W3EAX-13']

    if len(sys.argv) > 2:
        log_directory = sys.argv[2]
    else:
        log_directory = os.path.join(os.path.expanduser('~'), 'Desktop', 'log')

    if len(sys.argv) > 3:
        serial_port = sys.argv[3]
    else:
        serial_port = None

    if not os.path.exists(log_directory):
        os.mkdir(log_directory)

    log_filename = os.path.join(log_directory, f'{datetime.datetime.now().strftime("%Y%m%dT%H%M%S")}_huginn_log.txt')

    logbook.FileHandler(log_filename, level='DEBUG', bubble=True).push_application()
    logbook.StreamHandler(sys.stdout, level='INFO', bubble=True).push_application()
    logger = logbook.Logger('Huginn')

    ground_tracks = {}

    with radio.connect(serial_port) as radio_connection:
        logger.info(f'Serial connection established on {radio_connection.name}.')

        while True:
            raw_packets = radio.packets(radio_connection)

            for raw_packet in raw_packets:
                try:
                    parsed_packet = packets.APRSPacket(raw_packet)
                except parsing.PartialPacketError as error:
                    parsed_packet = None
                    logger.debug(f'PartialPacketError: {error} ("{raw_packet}")')

                if parsed_packet is not None:
                    callsign = parsed_packet['callsign']

                    for callsign in callsigns:
                        callsign_regex = re.compile(callsign)

                    if callsign in ground_tracks:
                        ground_tracks[callsign].append(parsed_packet)
                    else:
                        ground_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])

                    ascent_rate = ground_tracks[callsign].ascent_rate()
                    ground_speed = ground_tracks[callsign].ground_speed()
                    seconds_to_impact = ground_tracks[callsign].seconds_to_impact()

                    logger.info(
                        f'{parsed_packet} ascent_rate={ascent_rate} ground_speed={ground_speed} seconds_to_impact={seconds_to_impact}')

            time.sleep(1)
