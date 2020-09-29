from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from datetime import datetime
from getpass import getpass
import os
from pathlib import Path
import time

from client import CREDENTIALS_FILENAME, DEFAULT_INTERVAL_SECONDS
from client.gui import PacketRavenGUI
from packetraven.connections import APRSPacketDatabaseTable, APRSPacketRadio, APRSPacketTextFile, APRSfiConnection, \
    PacketDatabaseTable
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger, read_configuration
from packetraven.writer import write_aprs_packet_tracks

LOGGER = get_logger('packetraven')


def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--callsigns', nargs='?', const=None,
                        help='comma-separated list of callsigns to track')
    parser.add_argument('-k', '--apikey', help='API key from https://aprs.fi/page/api')
    parser.add_argument('-p', '--port', help='name of serial port connected to APRS packet radio')
    parser.add_argument('-d', '--database', help='PostGres database table `user@hostname:port/database/table`')
    parser.add_argument('-t', '--tunnel', help='SSH tunnel `user@hostname:port`')
    parser.add_argument('-l', '--log', help='path to log file to save log messages')
    parser.add_argument('-o', '--output', help='path to output file to save packets')
    parser.add_argument('-i', '--interval', default=DEFAULT_INTERVAL_SECONDS, type=float,
                        help='seconds between each main loop')
    parser.add_argument('-g', '--gui', action='store_true', help='start the graphical interface')
    args = parser.parse_args()

    using_gui = args.gui

    if args.callsigns is None and not using_gui:
        parser.error('the following arguments are required: -c/--callsigns')
    callsigns = args.callsigns.strip('"').split(',') if args.callsigns is not None else None

    kwargs = {'api_key': args.apikey, 'serial_port': args.port}

    if args.database is not None:
        database = args.database
        if database.count('/') != 2:
            LOGGER.error(f'unable to parse hostname, database name, and table name from input "{database}"')
        else:
            kwargs['hostname'], kwargs['database'], kwargs['table'] = database.split('/')
            if '@' in kwargs['hostname']:
                kwargs['username'], kwargs['hostname'] = kwargs['hostname'].split('@', 1)

    if args.tunnel is not None:
        kwargs['ssh_hostname'] = args.tunnel
        if '@' in kwargs['ssh_hostname']:
            kwargs['ssh_username'], kwargs['ssh_hostname'] = kwargs['ssh_hostname'].split('@', 1)

    if args.log is not None:
        log_filename = Path(args.log).expanduser()
        if log_filename.is_dir():
            if not log_filename.exists():
                os.makedirs(log_filename, exist_ok=True)
            log_filename = log_filename / f'{datetime.now():%Y%m%dT%H%M%S}_packetraven_log.txt'
        get_logger(LOGGER.name, log_filename)
    else:
        log_filename = None

    if args.output is not None:
        output_filename = Path(args.output).expanduser()
        output_directory = output_filename.parent
        if not output_directory.exists():
            os.makedirs(output_directory, exist_ok=True)
    else:
        output_filename = None

    interval_seconds = args.interval

    if CREDENTIALS_FILENAME.exists():
        credentials = {}
        for section in read_configuration(CREDENTIALS_FILENAME).values():
            credentials.update(section)
        kwargs = {key: value if key not in kwargs or kwargs[key] is None else kwargs[key]
                  for key, value in credentials.items()}

    if using_gui:
        PacketRavenGUI(callsigns, log_filename, output_filename, interval_seconds, **kwargs)
    else:
        connections = []
        if 'serial_port' in kwargs:
            radio_kwargs = {key: kwargs[key] for key in ['serial_port'] if key in kwargs}
            if radio_kwargs['serial_port'] is not None and 'txt' in radio_kwargs['serial_port']:
                try:
                    text_file = APRSPacketTextFile(kwargs['serial_port'])
                    LOGGER.info(f'reading file {text_file.location}')
                    connections.append(text_file)
                except ConnectionError as error:
                    LOGGER.warning(f'{error.__class__.__name__} - {error}')
            else:
                try:
                    radio = APRSPacketRadio(kwargs['serial_port'])
                    LOGGER.info(f'opened port {radio.location}')
                    connections.append(radio)
                except ConnectionError as error:
                    LOGGER.warning(f'{error.__class__.__name__} - {error}')

        if 'api_key' in kwargs:
            aprs_fi_kwargs = {key: kwargs[key] for key in ['api_key'] if key in kwargs}
            try:
                aprs_api = APRSfiConnection(callsigns=callsigns, **aprs_fi_kwargs)
                LOGGER.info(f'connected to {aprs_api.location} with selected callsigns: {", ".join(callsigns)}')
                connections.append(aprs_api)
            except ConnectionError as error:
                LOGGER.warning(f'{error.__class__.__name__} - {error}')

        if 'hostname' in kwargs:
            database_kwargs = {key: kwargs[key]
                               for key in ['hostname', 'database', 'table', 'username', 'password',
                                           'ssh_hostname', 'ssh_username', 'ssh_password'] if key in kwargs}
            if 'ssh_username' not in database_kwargs:
                database_kwargs['ssh_username'] = input('SSH username: ')
            if 'ssh_password' not in database_kwargs or database_kwargs['ssh_password'] is None:
                database_kwargs['ssh_password'] = getpass('SSH password: ')

            if 'username' not in database_kwargs:
                database_kwargs['username'] = input(f'database username: ')
            if 'password' not in database_kwargs:
                database_kwargs['password'] = getpass('database password: ')

            database = APRSPacketDatabaseTable(callsigns=callsigns, **database_kwargs)
            LOGGER.info(f'connected to {database.location} with selected callsigns: {", ".join(callsigns)}')
            connections.append(database)
        else:
            database = None

        packet_tracks = {}
        while len(connections) > 0:
            LOGGER.debug(f'receiving packets from {len(connections)} source(s)')

            parsed_packets = []
            for connection in connections:
                parsed_packets.extend(connection.packets)

            LOGGER.debug(f'received {len(parsed_packets)} packets')

            if len(parsed_packets) > 0:
                for parsed_packet in parsed_packets:
                    callsign = parsed_packet['callsign']

                    if callsign not in packet_tracks:
                        packet_tracks[callsign] = APRSTrack(callsign, [parsed_packet])
                        LOGGER.debug(f'started tracking {callsign:8}')
                    else:
                        packet_track = packet_tracks[callsign]
                        if parsed_packet not in packet_track:
                            packet_track.append(parsed_packet)
                        else:
                            if not isinstance(parsed_packet.source, PacketDatabaseTable):
                                LOGGER.debug(f'skipping duplicate packet: {parsed_packet}')
                            continue

                    LOGGER.info(f'new packet from {parsed_packet.source.location}: {parsed_packet}')

                    if database is not None:
                        LOGGER.info(f'sending packet to {database.location}')
                        database.insert([parsed_packet])

                    if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                        ascent_rate = packet_tracks[callsign].ascent_rate[-1]
                        ground_speed = packet_tracks[callsign].ground_speed[-1]
                        seconds_to_impact = packet_tracks[callsign].seconds_to_impact
                        LOGGER.info(f'{callsign:8} ascent rate      : {ascent_rate} m/s')
                        LOGGER.info(f'{callsign:8} ground speed     : {ground_speed} m/s')
                        if seconds_to_impact >= 0:
                            LOGGER.info(f'{callsign:8} estimated landing: {seconds_to_impact} s')

                if output_filename is not None:
                    write_aprs_packet_tracks(packet_tracks.values(), output_filename)

            time.sleep(interval_seconds)


if __name__ == '__main__':
    main()
