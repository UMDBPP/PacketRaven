from argparse import ArgumentParser
from datetime import datetime
from getpass import getpass
import os
from pathlib import Path
import time

from client import CREDENTIALS_FILENAME, DEFAULT_INTERVAL_SECONDS
from client.gui import PacketRavenGUI
from client.retrieve import retrieve_packets
from packetraven.connections import APRSPacketDatabaseTable, APRSPacketRadio, APRSPacketTextFile, \
    APRSfiConnection
from packetraven.utilities import get_logger, read_configuration

LOGGER = get_logger('packetraven')


def main():
    args_parser = ArgumentParser()
    args_parser.add_argument('-c', '--callsigns', help='comma-separated list of callsigns to track')
    args_parser.add_argument('-k', '--apikey', help='API key from https://aprs.fi/page/api')
    args_parser.add_argument('-p', '--port', help='name of serial port connected to APRS packet radio '
                                                  '(set to `auto` to connect to the first open serial port)')
    args_parser.add_argument('-d', '--database', help='PostGres database table `user@hostname:port/database/table`')
    args_parser.add_argument('-t', '--tunnel', help='SSH tunnel `user@hostname:port`')
    args_parser.add_argument('-l', '--log', help='path to log file to save log messages')
    args_parser.add_argument('-o', '--output', help='path to output file to save packets')
    args_parser.add_argument('-i', '--interval', default=DEFAULT_INTERVAL_SECONDS, type=float,
                             help='seconds between each main loop (default: 10)')
    args_parser.add_argument('-g', '--gui', action='store_true', help='start the graphical interface')
    args = args_parser.parse_args()

    using_gui = args.gui

    callsigns = [callsign.upper() for callsign in args.callsigns.strip('"').split(',')] if args.callsigns is not None else None

    kwargs = {'api_key': args.apikey}

    if args.port is not None:
        kwargs['serial_port'] = args.port

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
        if callsigns is not None:
            LOGGER.info(f'filtering by {len(callsigns)}')

        connections = []
        if 'serial_port' in kwargs:
            radio_kwargs = {key: kwargs[key] for key in ['serial_port'] if key in kwargs}
            if radio_kwargs['serial_port'] is not None and 'txt' in radio_kwargs['serial_port']:
                try:
                    text_file = APRSPacketTextFile(kwargs['serial_port'], callsigns)
                    LOGGER.info(f'reading file {text_file.location}')
                    connections.append(text_file)
                except ConnectionError as error:
                    LOGGER.warning(f'{error.__class__.__name__} - {error}')
            else:
                try:
                    radio = APRSPacketRadio(kwargs['serial_port'], callsigns)
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
                               for key in ['hostname', 'database', 'table', 'username', 'password', ]
                               if key in kwargs}
            ssh_tunnel_kwargs = {key: kwargs[key]
                                 for key in ['ssh_hostname', 'ssh_username', 'ssh_password']
                                 if key in kwargs}
            if 'ssh_username' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_username'] is None:
                ssh_tunnel_kwargs['ssh_username'] = input('enter SSH username: ')
            if 'ssh_password' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_password'] is None:
                ssh_tunnel_kwargs['ssh_password'] = getpass('enter SSH password: ')

            if 'username' not in database_kwargs or database_kwargs['username'] is None:
                database_kwargs['username'] = input(f'enter database username: ')
            if 'password' not in database_kwargs or database_kwargs['password'] is None:
                database_kwargs['password'] = getpass('enter database password: ')

            database = APRSPacketDatabaseTable(**database_kwargs, **ssh_tunnel_kwargs, callsigns=callsigns)
            LOGGER.info(f'connected to {database.location}')
            connections.append(database)
        else:
            database = None

        LOGGER.info(f'opened {len(connections)} connections')

        packet_tracks = {}
        while len(connections) > 0:
            retrieve_packets(connections, packet_tracks, database, output_filename, LOGGER)
            time.sleep(interval_seconds)
        else:
            LOGGER.warning(f'no connections started')


if __name__ == '__main__':
    main()
