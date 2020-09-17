import argparse
from datetime import datetime
import os
from pathlib import Path
import time

from packetraven import DEFAULT_CALLSIGNS
from packetraven.connections import APRS_fi, PacketRadio, PacketTextFile
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger
from packetraven.writer import write_aprs_packet_tracks

LOGGER = get_logger('packetraven')

DEFAULT_INTERVAL_SECONDS = 5
DESKTOP_PATH = Path('~').expanduser() / 'Desktop'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', help='API key from https://aprs.fi/page/api')
    parser.add_argument('-c', '--callsigns', help='comma-separated list of callsigns to track')
    parser.add_argument('-r', '--noradio', action='store_true', help='skip attempting to connect to APRS packet radio')
    parser.add_argument('-p', '--port', help='name of serial port connected to APRS packet radio')
    parser.add_argument('-l', '--log', help='path to log file to save log messages')
    parser.add_argument('-o', '--output', help='path to output file to save packets')
    parser.add_argument('-t', '--interval', help='seconds between each main loop')
    args = parser.parse_args()

    aprs_fi_api_key = args.key

    callsigns = args.callsigns.strip('"').split(',') if args.callsigns is not None else DEFAULT_CALLSIGNS

    if args.log is not None:
        log_filename = Path(args.log).expanduser()
        if log_filename.is_dir():
            if not log_filename.exists():
                os.makedirs(log_filename, exist_ok=True)
            log_filename = log_filename / f'{datetime.now():%Y%m%dT%H%M%S}_packetraven_log.txt'
        get_logger(LOGGER.name, log_filename)

    if args.output is not None:
        output_filename = Path(args.output).expanduser()
        output_directory = output_filename.parent
        if not output_directory.exists():
            os.makedirs(output_directory, exist_ok=True)
    else:
        output_filename = None

    serial_port = args.port

    aprs_connections = []
    if not args.noradio:
        if serial_port is not None and 'txt' in serial_port:
            try:
                text_file = PacketTextFile(serial_port)
                aprs_connections.append(text_file)
            except ConnectionError as error:
                LOGGER.warning(f'{error.__class__.__name__} - {error}')
        else:
            try:
                radio = PacketRadio(serial_port)
                serial_port = radio.location
                LOGGER.info(f'opened port {serial_port}')
                aprs_connections.append(radio)
            except ConnectionError as error:
                LOGGER.warning(f'{error.__class__.__name__} - {error}')

    try:
        aprs_api = APRS_fi(callsigns, api_key=aprs_fi_api_key)
        LOGGER.info(f'connected to {aprs_api.location} with selected callsigns: {", ".join(callsigns)}')
        aprs_connections.append(aprs_api)
    except ConnectionError as error:
        LOGGER.warning(f'{error.__class__.__name__} - {error}')

    packet_tracks = {}
    while len(aprs_connections) > 0:
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

        time.sleep(DEFAULT_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
