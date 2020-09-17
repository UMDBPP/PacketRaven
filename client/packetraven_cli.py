"""
Balloon telemetry parsing, display, and logging.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

from datetime import datetime
import os
from pathlib import Path
import sys
import time

from packetraven import BALLOON_CALLSIGNS
from packetraven.connections import APRS_fi, PacketRadio, PacketTextFile
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger
from packetraven.writer import write_aprs_packet_tracks

INTERVAL_SECONDS = 5
DESKTOP_PATH = Path('~').resolve() / 'Desktop'

LOGGER = get_logger('packetraven')


def main():
    if len(sys.argv) > 0 and '-h' not in sys.argv:
        serial_port = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
        log_filename = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else DESKTOP_PATH
        output_filename = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None

        if log_filename.is_dir():
            if not log_filename.exists():
                os.makedirs(log_filename, exist_ok=True)
            log_filename = log_filename / f'{datetime.now():%Y%m%dT%H%M%S}_packetraven_log.txt'

        if output_filename is not None:
            output_directory = output_filename.parent
            if not output_directory.exists():
                os.makedirs(output_directory, exist_ok=True)

        get_logger(LOGGER.name, log_filename)

        aprs_connections = []
        if serial_port is not None and 'txt' in serial_port:
            try:
                text_file = PacketTextFile(serial_port)
                aprs_connections.append(text_file)
            except Exception as error:
                LOGGER.exception(f'{error.__class__.__name__} - {error}')
        else:
            try:
                radio = PacketRadio(serial_port)
                serial_port = radio.serial_port
                LOGGER.info(f'opened port {serial_port}')
                aprs_connections.append(radio)
            except Exception as error:
                LOGGER.exception(f'{error.__class__.__name__} - {error}')

        try:
            aprs_api = APRS_fi(BALLOON_CALLSIGNS)
            LOGGER.info(f'established connection to API')
            aprs_connections.append(aprs_api)
        except Exception as error:
            LOGGER.exception(f'{error.__class__.__name__} - {error}')

        packet_tracks = {}
        while True:
            LOGGER.debug(f'receiving packets from {len(aprs_connections)} source(s)')

            parsed_packets = []
            for aprs_connection in aprs_connections:
                parsed_packets.extend(aprs_connection.packets)

            LOGGER.debug(f'received {len(parsed_packets)} packets')

            if len(parsed_packets) > 0:
                for parsed_packet in parsed_packets:
                    callsign = parsed_packet['callsign']

                    if callsign in packet_tracks:
                        if parsed_packet not in packet_tracks[callsign]:
                            packet_tracks[callsign].append(parsed_packet)
                        else:
                            LOGGER.debug(f'{callsign:8} - received duplicate packet: {parsed_packet}')
                            continue
                    else:
                        packet_tracks[callsign] = APRSTrack(callsign, [parsed_packet])
                        LOGGER.debug(f'{callsign:8} - started tracking')

                    LOGGER.info(f'{callsign:8} - received new packet: {parsed_packet}')

                    if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                        ascent_rate = packet_tracks[callsign].ascent_rate[-1]
                        ground_speed = packet_tracks[callsign].ground_speed[-1]
                        seconds_to_impact = packet_tracks[callsign].seconds_to_impact
                        LOGGER.info(f'{callsign:8} - Ascent rate (m/s): {ascent_rate}')
                        LOGGER.info(f'{callsign:8} - Ground speed (m/s): {ground_speed}')
                        if seconds_to_impact >= 0:
                            LOGGER.info(f'{callsign:8} - Estimated time until landing (s): {seconds_to_impact}')

                if output_filename is not None:
                    write_aprs_packet_tracks(packet_tracks.values(), output_filename)

            time.sleep(INTERVAL_SECONDS)
    else:
        print('usage: packetraven serial_port [log_path] [output_file]')


if __name__ == '__main__':
    main()
