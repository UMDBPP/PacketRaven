"""
Balloon telemetry parsing, display, and logging.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import logging
import os
import sys
import time
from datetime import datetime

from huginn import radio, tracks
from huginn.writer import write_aprs_packet_tracks

if __name__ == '__main__':
    if len(sys.argv) > 0 and '-h' not in sys.argv:
        serial_port = sys.argv[1] if len(sys.argv) > 1 else None
        log_filename = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.expanduser('~'), 'Desktop')
        output_filename = sys.argv[3] if len(sys.argv) > 3 else None

        if os.path.isdir(log_filename):
            if not os.path.exists(log_filename):
                os.mkdir(log_filename)
            log_filename = os.path.join(log_filename, f'{datetime.now():%Y%m%dT%H%M%S}_huginn_log.txt')

        if output_filename is not None:
            if not os.path.exists(output_filename):
                raise EnvironmentError(f'output file does not exist: {output_filename}')
            elif os.path.isfile(output_filename):
                output_filename = os.path.dirname(output_filename)

        radio_connection = radio.Radio(serial_port)

        logging.basicConfig(filename=log_filename, level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                            format='[%(asctime)s] %(levelname)s: %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        logging.getLogger('').addHandler(console)

        packet_tracks = {}

        logging.info(f'Opening {radio_connection.serial_port}.')

        while True:
            parsed_packets = radio_connection.read()

            for parsed_packet in parsed_packets:
                callsign = parsed_packet['callsign']

                if callsign in packet_tracks:
                    packet_tracks[callsign].append(parsed_packet)
                else:
                    packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])

                message = f'{parsed_packet}'

                if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                    ascent_rate = packet_tracks[callsign].ascent_rate
                    ground_speed = packet_tracks[callsign].ground_speed
                    seconds_to_impact = packet_tracks[callsign].seconds_to_impact
                    message += f'ascent_rate={ascent_rate} ground_speed={ground_speed} seconds_to_impact={seconds_to_impact}'

                logging.info(message)

            if output_filename is not None:
                write_aprs_packet_tracks(packet_tracks.values(), output_filename)

            time.sleep(1)
    else:
        print('usage: huginn serial_port [log_path] [output_file]')
