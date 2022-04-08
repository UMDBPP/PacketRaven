from copy import copy
from datetime import datetime, timedelta
from getpass import getpass
import logging
from pathlib import Path
import sys
import time
from typing import Dict, List

from dateutil.tz import tzlocal
import humanize as humanize
import numpy
import typer

from packetraven.configuration.prediction import PredictionConfiguration
from packetraven.configuration.run import RunConfiguration
from packetraven.connections import (
    PacketDatabaseTable,
    PacketGeoJSON,
    RawAPRSTextFile,
    SerialTNC,
    TimeIntervalError,
)
from packetraven.connections.base import PacketSource
from packetraven.packets import APRSPacket
from packetraven.packets.tracks import APRSTrack, LocationPacketTrack, PredictedTrajectory
from packetraven.packets.writer import write_packet_tracks
from packetraven.predicts import CUSFBalloonPredictionQuery, PredictionError

logging.basicConfig(
    stream=sys.stdout, level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s'
)

DEFAULT_INTERVAL_SECONDS = 20


def packetraven_command(configuration_filename: str, gui: bool = False):
    """
    start parsing packets

    :param configuration_filename: configuration file in YAML format - see `examples` directory for examples
    :param gui: start the graphical interface
    """

    program_start_time = datetime.now()

    if not isinstance(configuration_filename, Path):
        configuration_filename = Path(configuration_filename)

    if configuration_filename is not None:
        configuration = RunConfiguration.from_file(configuration_filename)

        if configuration['log'] is not None:
            if (
                'filename' not in configuration['log']
                or configuration['log']['filename'] is None
            ):
                configuration['log']['filename'] = Path('.')
            if configuration['log']['filename'].is_dir():
                configuration['log'][
                    'filename'
                ] /= f'{configuration["name"]}_log_{program_start_time:%Y%m%dT%H%M%S}.txt'
            logging.basicConfig(filename=configuration['log']['filename'])

        if configuration['output'] is not None:
            if (
                'filename' not in configuration['output']
                or configuration['output']['filename'] is None
            ):
                configuration['output']['filename'] = Path('.')
            if configuration['output']['filename'].is_dir():
                configuration['output'][
                    'filename'
                ] /= f'{configuration["name"]}_{program_start_time:%Y%m%dT%H%M%S}.geojson'

        if 'prediction' in configuration and configuration['prediction'] is not None:
            if configuration['prediction']['output']['filename'] is None:
                configuration['prediction']['output']['filename'] = Path('.')
            if configuration['prediction']['output']['filename'].is_dir():
                configuration['prediction']['output'][
                    'filename'
                ] /= f'{configuration["name"]}_predict_{program_start_time:%Y%m%dT%H%M%S}.geojson'

        filter_message = 'retrieving packets'
        if configuration['time']['start'] is not None and configuration['time']['end'] is None:
            filter_message += f' sent after {configuration["time"]["start"]:%Y-%m-%d %H:%M:%S}'
        elif (
            configuration['time']['start'] is None and configuration['time']['end'] is not None
        ):
            filter_message += f' sent before {configuration["time"]["end"]:%Y-%m-%d %H:%M:%S}'
        elif (
            configuration['time']['start'] is not None
            and configuration['time']['end'] is not None
        ):
            filter_message += (
                f' sent between {configuration["time"]["start"]:%Y-%m-%d %H:%M:%S}'
                f' and {configuration["time"]["end"]:%Y-%m-%d %H:%M:%S}'
            )
        if configuration['callsigns'] is not None:
            filter_message += f' from {len(configuration["callsigns"])} callsigns: {configuration["callsigns"]}'
        logging.info(filter_message)

        if configuration['callsigns'] is not None:
            aprsfi_url = (
                f'https://aprs.fi/#!call=a%2F{"%2Ca%2F".join(configuration["callsigns"])}'
            )
            if configuration['time']['start'] is not None:
                aprsfi_url += f'&ts={configuration["time"]["start"]:%s}'
            if configuration['time']['end'] is not None:
                aprsfi_url += f'&te={configuration["time"]["end"]:%s}'
            logging.info(f'tracking URL: {aprsfi_url}')
    else:
        configuration = None

    if gui:
        from packetraven.gui import PacketRavenGUI

        PacketRavenGUI(configuration)
    elif configuration is not None:
        connections = []
        if 'text' in configuration['packets']:
            for location in configuration['packets']['text']['locations']:
                location = location.strip()
                try:
                    if Path(location).suffix in ['.txt', '.log']:
                        connection = RawAPRSTextFile(location, configuration['callsigns'])
                        logging.info(f'reading text file {connection.location}')
                    elif Path(location).suffix in ['.json', '.geojson']:
                        connection = PacketGeoJSON(
                            location, callsigns=configuration['callsigns']
                        )
                        logging.info(f'reading GeoJSON file {connection.location}')
                    else:
                        connection = SerialTNC(location, configuration['callsigns'])
                        logging.info(f'opened port {connection.location} for APRS parsing')
                    connections.append(connection)
                except ConnectionError as error:
                    logging.warning(f'{error.__class__.__name__} - {error}')

        if 'aprs_fi' in configuration['packets']:
            try:
                aprs_api = configuration['packets']['aprs_fi'].packet_source(
                    callsigns=configuration['callsigns']
                )
                logging.info(f'connected to {aprs_api.location}')
                connections.append(aprs_api)
            except ConnectionError as error:
                logging.warning(f'{error.__class__.__name__} - {error}')

        if 'database' in configuration['packets']:
            database_credentials = configuration['packets']['database']
            ssh_tunnel_credentials = database_credentials['tunnel']
            try:
                if ssh_tunnel_credentials is not None:
                    if ssh_tunnel_credentials['username'] is None:
                        ssh_username = input(
                            f'enter username for SSH host "{ssh_tunnel_credentials["hostname"]}": '
                        )
                        if ssh_username is None or len(ssh_username) == 0:
                            raise ConnectionError('missing SSH username')
                        ssh_tunnel_credentials['username'] = ssh_username

                    if ssh_tunnel_credentials['password'] is None:
                        ssh_password = getpass(
                            f'enter password for SSH user "{ssh_tunnel_credentials["username"]}": '
                        )
                        if ssh_password is None or len(ssh_password) == 0:
                            raise ConnectionError('missing SSH password')
                        ssh_tunnel_credentials['password'] = ssh_password

                if database_credentials['username'] is None:
                    database_username = input(
                        f'enter username for database '
                        f'"{database_credentials["hostname"]}/{database_credentials["database"]}": '
                    )
                    if database_username is None or len(database_username) == 0:
                        raise ConnectionError('missing database username')
                    database_credentials['username'] = database_username

                if database_credentials['password'] is None:
                    database_password = getpass(
                        f'enter password for database user "{database_credentials["username"]}": '
                    )
                    if database_password is None or len(database_password) == 0:
                        raise ConnectionError('missing database password')
                    database_credentials['password'] = database_password

                database = database_credentials.packet_source(
                    callsigns=configuration['callsigns']
                )
                logging.info(f'connected to {database.location}')
                connections.append(database)
            except ConnectionError:
                database = None
        else:
            database = None

        if len(connections) == 0:
            if (
                configuration['output']['filename'] is not None
                and configuration['output']['filename'].exists()
            ):
                connections.append(PacketGeoJSON(configuration['output']['filename']))
            else:
                logging.error(f'no connections started')
                sys.exit(1)

        if 'aprs_is' in configuration['packets']:
            try:
                aprs_is = configuration['packets']['aprs_is'].packet_source(
                    callsigns=configuration['callsigns']
                )
            except ConnectionError:
                aprs_is = None
        else:
            aprs_is = None

        logging.info(
            f'listening for packets every {configuration["time"]["interval"]}s from {len(connections)} connection(s): '
            f'{", ".join([connection.location for connection in connections])}'
        )

        packet_tracks = {}
        predictions = {}
        plots = {}

        if any(configuration['plots'].values()):
            from packetraven.gui.plotting import LiveTrackPlot

            for variable, enabled in configuration['plots'].items():
                if enabled and variable not in plots:
                    plots[variable] = LiveTrackPlot(packet_tracks, variable, predictions)
                elif not enabled and variable in plots:
                    plots[variable].close()
                    del plots[variable]

        try:
            time_without_packets = timedelta(seconds=0)
            while len(connections) > 0:
                current_time = datetime.now()

                try:
                    new_packets = retrieve_packets(
                        connections,
                        packet_tracks,
                        database,
                        start_date=configuration['time']['start'],
                        end_date=configuration['time']['end'],
                    )

                    output_filename_index = None
                    for index, connection in enumerate(connections):
                        if isinstance(connection, PacketGeoJSON):
                            output_filename_index = index
                    if output_filename_index is not None:
                        connections.pop(output_filename_index)

                    if configuration['prediction'] is not None:
                        try:
                            predictions.update(
                                packet_track_predictions(
                                    packet_tracks, configuration['prediction'],
                                )
                            )
                            write_packet_tracks(
                                predictions.values(),
                                configuration['prediction']['output']['filename'],
                            )
                        except PredictionError as error:
                            logging.warning(f'{error.__class__.__name__} - {error}')
                        except Exception as error:
                            logging.warning(
                                f'error retrieving prediction trajectory - {error.__class__.__name__} - {error}'
                            )
                except Exception as error:
                    logging.exception(f'{error.__class__.__name__} - {error}')
                    new_packets = {}

                for plot in plots.values():
                    plot.update(packet_tracks, predictions)

                if len(new_packets) > 0:
                    if configuration['output']['filename'] is not None:
                        write_packet_tracks(
                            [packet_tracks[callsign] for callsign in packet_tracks],
                            configuration['output']['filename'],
                        )
                    if aprs_is is not None:
                        for packets in new_packets.values():
                            aprs_is.send(packets)
                else:
                    time_without_packets += configuration['time']['interval'] + (
                        datetime.now() - current_time
                    )

                if (
                    'timeout' in configuration['time']
                    and time_without_packets >= configuration['time']['timeout']
                ):
                    logging.info(
                        f'shutting down - no packets received for {time_without_packets}'
                    )
                    break
                else:
                    time.sleep(configuration['time']['interval'] / timedelta(seconds=1))
        except KeyboardInterrupt:
            for connection in connections:
                connection.close()
            sys.exit(0)
    else:
        logging.error(
            'no configuration given; to use the graphical interface try `packetraven --gui`'
        )
        sys.exit(1)


def retrieve_packets(
    connections: List[PacketSource],
    packet_tracks: List[LocationPacketTrack],
    database: PacketDatabaseTable = None,
    start_date: datetime = None,
    end_date: datetime = None,
) -> Dict[str, APRSPacket]:
    logging.debug(f'receiving packets from {len(connections)} source(s)')
    current_time = datetime.now()

    parsed_packets = []
    for connection in connections:
        try:
            connection_packets = connection.packets
            parsed_packets.extend(connection_packets)
        except ConnectionError as error:
            logging.error(f'{connection.__class__.__name__} - {error}')
        except TimeIntervalError:
            pass

    logging.debug(f'received {len(parsed_packets)} packets')

    new_packets = {}
    if len(parsed_packets) > 0:
        updated_callsigns = set()
        for parsed_packet in parsed_packets:
            callsign = parsed_packet['callsign']

            start_date = ensure_datetime_timezone(start_date)
            end_date = ensure_datetime_timezone(end_date)
            parsed_packet.time = ensure_datetime_timezone(parsed_packet.time)

            if start_date is not None and parsed_packet.time < start_date:
                continue
            if end_date is not None and parsed_packet.time > end_date:
                continue

            if callsign not in packet_tracks:
                packet_tracks[callsign] = APRSTrack(packets=[parsed_packet], callsign=callsign)
                logging.debug(f'started tracking callsign {callsign:8}')
            else:
                packet_track = packet_tracks[callsign]
                if parsed_packet not in packet_track:
                    packet_track.append(parsed_packet)
                else:
                    if database is None or parsed_packet.source != database.location:
                        logging.debug(f'skipping duplicate packet: {parsed_packet}')
                    continue

            if parsed_packet.source not in new_packets:
                new_packets[parsed_packet.source] = []
            new_packets[parsed_packet.source].append(parsed_packet)
            if callsign not in updated_callsigns:
                updated_callsigns.add(callsign)

        for source in new_packets:
            new_packets[source] = list(sorted(new_packets[source]))

        for source, packets in new_packets.items():
            logging.info(f'received {len(packets)} new packet(s) from {source}')

        if database is not None:
            for packets in new_packets.values():
                database.send(
                    packet for packet in packets if packet.source != database.location
                )

        updated_callsigns = sorted(updated_callsigns)
        for callsign in updated_callsigns:
            packet_track = packet_tracks[callsign]
            packet_time = datetime.utcfromtimestamp(
                (packet_track.times[-1] - numpy.datetime64('1970-01-01T00:00:00'))
                / numpy.timedelta64(1, 's')
            )
            packet_track.sort(inplace=True)
            try:
                coordinate_string = ', '.join(
                    f'{coordinate:.3f}°' for coordinate in packet_track.coordinates[-1, :2]
                )
                logging.info(
                    f'{callsign:9} - packet #{len(packet_track):<3} - ({coordinate_string}, {packet_track.coordinates[-1, 2]:9.2f}m)'
                    f'; packet time is {packet_time} ({humanize.naturaltime(current_time - packet_time)}, {packet_track.intervals[-1] / numpy.timedelta64(1, "s"):6.1f} s interval)'
                    f'; traveled {packet_track.overground_distances[-1]:6.1f} m ({packet_track.ground_speeds[-1]:5.1f} m/s) over the ground'
                    f', and {packet_track.ascents[-1]:6.1f} m ({packet_track.ascent_rates[-1]:5.1f} m/s) vertically, since the previous packet'
                )
            except Exception as error:
                logging.exception(f'{error.__class__.__name__} - {error}')

        for callsign in updated_callsigns:
            packet_track = packet_tracks[callsign]
            packet_time = datetime.utcfromtimestamp(
                (packet_track.times[-1] - numpy.datetime64('1970-01-01T00:00:00'))
                / numpy.timedelta64(1, 's')
            )
            try:
                ascent_rates = packet_track.ascent_rates[packet_track.ascent_rates >= 0]
                if len(ascent_rates) > 0:
                    mean_ascent_rate = numpy.nanmean(ascent_rates)
                else:
                    mean_ascent_rate = 0

                descent_rates = packet_track.ascent_rates[packet_track.ascent_rates < 0]
                if len(descent_rates) > 0:
                    mean_descent_rate = numpy.nanmean(descent_rates)
                else:
                    mean_descent_rate = 0

                if len(packet_track.ground_speeds) > 0:
                    mean_ground_speed = numpy.nanmean(packet_track.ground_speeds)
                else:
                    mean_ground_speed = 0

                if len(packet_track.intervals) > 0:
                    mean_interval = numpy.nanmean(
                        packet_track.intervals / numpy.timedelta64(1, 's')
                    )
                else:
                    mean_interval = 0

                message = (
                    f'{callsign:9} - '
                    f'altitude: {packet_track.altitudes[-1]:6.1f} m'
                    f'; avg. ascent rate: {mean_ascent_rate:5.1f} m/s'
                    f'; avg. descent rate: {mean_descent_rate:5.1f} m/s'
                    f'; avg. ground speed: {mean_ground_speed:5.1f} m/s'
                    f'; avg. packet interval: {mean_interval:6.1f} s'
                )

                if packet_track.time_to_ground >= timedelta(seconds=0):
                    landing_time = packet_time + packet_track.time_to_ground
                    time_to_ground = current_time - landing_time
                    message += (
                        f'; estimated landing: {landing_time:%Y-%m-%d %H:%M:%S} ({humanize.naturaltime(time_to_ground)})'
                        f'; max altitude: {packet_track.coordinates[:, 2].max():.2f} m'
                    )

                logging.info(message)

            except Exception as error:
                logging.exception(f'{error.__class__.__name__} - {error}')

    return new_packets


def packet_track_predictions(
    packet_tracks: Dict[str, LocationPacketTrack], configuration=PredictionConfiguration,
) -> Dict[str, PredictedTrajectory]:
    """
    retrieve location tracks detailing predicted trajectory of balloon flight(s) from the current track location

    :param packet_tracks: location packet tracks
    :param configuration: prediction configuration
    """

    prediction_tracks = {}
    for name, packet_track in packet_tracks.items():
        track_configuration = copy(configuration)

        ascent_rates = packet_track.ascent_rates[packet_track.ascent_rates > 0]
        if len(ascent_rates) > 0:
            average_ascent_rate = numpy.mean(ascent_rates)
            if average_ascent_rate > 0:
                track_configuration['profile']['ascent_rate'] = average_ascent_rate

            # if packet track is descending, override given burst altitude
            if len(ascent_rates) > 2 and all(ascent_rates[-2:] < 0):
                track_configuration['profile']['burst_altitude'] = (
                    packet_track.altitudes[-1] + 1
                )

        last_packet = packet_track[-1]

        track_configuration['start']['time'] = last_packet.time

        track_configuration['start']['location'] = last_packet.coordinates
        if len(track_configuration['start']['location'].shape) > 1:
            track_configuration['start']['location'] = track_configuration['start'][
                'location'
            ][0, :]

        if track_configuration['float']['altitude'] is not None and not packet_track.falling:
            packets_at_float_altitude = packet_track[
                numpy.abs(track_configuration['float']['altitude'] - packet_track.altitudes)
                < track_configuration['float']['uncertainty']
            ]
            if (
                len(packets_at_float_altitude) > 0
                and packets_at_float_altitude[-1].time == packet_track.times[-1]
            ):
                track_configuration['float']['start_time'] = packets_at_float_altitude[0].time
                track_configuration['profile']['descent_only'] = False
            elif packet_track.ascent_rates[-1] >= 0:
                track_configuration['float']['start_time'] = track_configuration['start'][
                    'time'
                ] + timedelta(
                    seconds=(
                        track_configuration['float']['altitude']
                        - track_configuration['start']['location'][2]
                    )
                    / track_configuration['profile']['ascent_rate']
                )
                track_configuration['profile']['descent_only'] = False
            else:
                track_configuration['float']['start_time'] = None
                track_configuration['profile']['descent_only'] = True
                track_configuration['profile'][
                    'sea_level_descent_rate'
                ] = packet_track.ascent_rates[-1]
        else:
            track_configuration['profile']['descent_only'] = packet_track.falling or numpy.any(
                packet_track.ascent_rates[-2:] < 0
            )

        try:
            prediction_query = CUSFBalloonPredictionQuery(
                start_location=track_configuration['start']['location'],
                start_time=track_configuration['start']['time'],
                ascent_rate=track_configuration['profile']['ascent_rate'],
                burst_altitude=track_configuration['profile']['burst_altitude'],
                sea_level_descent_rate=track_configuration['profile'][
                    'sea_level_descent_rate'
                ],
                float_altitude=track_configuration['float']['altitude'],
                float_duration=track_configuration['float']['duration'],
                api_url=track_configuration['api_url'],
                name=name,
                descent_only=track_configuration['profile']['descent_only'],
            )

            prediction = prediction_query.predict

            if packet_track.time_to_ground >= timedelta(seconds=0):
                logging.info(
                    f'{packet_track.name:<9} - predicted landing location: {prediction.coordinates[-1]} - https://www.google.com/maps/place/{prediction.coordinates[-1][1]},{prediction.coordinates[-1][0]}'
                )

            prediction_tracks[name] = prediction
        except Exception as error:
            logging.warning(
                f'error retrieving prediction trajectory - {error.__class__.__name__} - {error}'
            )

    if all(
        value is not None
        for value in [
            configuration['start']['location'],
            configuration['start']['time'],
            configuration['profile']['ascent_rate'],
            configuration['profile']['burst_altitude'],
            configuration['profile']['sea_level_descent_rate'],
        ]
    ):
        name = 'flight'

        try:
            prediction_query = CUSFBalloonPredictionQuery(
                start_location=configuration['start']['location'],
                start_time=configuration['start']['time'],
                ascent_rate=configuration['profile']['ascent_rate'],
                burst_altitude=configuration['profile']['burst_altitude'],
                sea_level_descent_rate=configuration['profile']['sea_level_descent_rate'],
                float_altitude=configuration['float']['altitude'],
                float_duration=configuration['float']['duration'],
                api_url=configuration['api_url'],
                name=name,
                descent_only=configuration['profile']['descent_only'],
            )

            prediction = prediction_query.predict
            prediction_tracks[name] = prediction
        except Exception as error:
            logging.warning(
                f'error retrieving prediction trajectory - {error.__class__.__name__} - {error}'
            )

    return prediction_tracks


def ensure_datetime_timezone(value: datetime) -> datetime:
    if value is not None and (value.tzinfo is None or value.tzinfo.utcoffset(value) is None):
        value = value.replace(tzinfo=tzlocal())
    return value


def main():
    typer.run(packetraven_command)


if __name__ == '__main__':
    main()
