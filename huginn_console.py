"""
Balloon telemetry parsing, display, and logging.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import datetime
import logging
import os
import sys
import time

from huginn import radio, tracks

if __name__ == '__main__':
    if len(sys.argv) > 0 and '-h' not in sys.argv:
        if len(sys.argv) > 1:
            serial_port = sys.argv[1]
        else:
            serial_port = None

        if len(sys.argv) > 2:
            log_filename = sys.argv[2]
        else:
            log_filename = os.path.join(os.path.expanduser('~'), 'Desktop')

        if os.path.isdir(log_filename):
            if not os.path.exists(log_filename):
                os.mkdir(log_filename)
            log_filename = os.path.join(log_filename,
                                        f'{datetime.datetime.now().strftime("%Y%m%dT%H%M%S")}_huginn_log.txt')

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

                ascent_rate = packet_tracks[callsign].ascent_rate()
                ground_speed = packet_tracks[callsign].ground_speed()
                seconds_to_impact = packet_tracks[callsign].seconds_to_impact()

                logging.info(
                    f'{parsed_packet} ascent_rate={ascent_rate} ground_speed={ground_speed} seconds_to_impact={seconds_to_impact}')

            time.sleep(1)
    else:
        print('usage: huginn serial_port [log_path]')
