from datetime import datetime, timedelta
from logging import Logger
from os import PathLike
from pathlib import Path

from aprslib.packets.base import APRSPacket
import numpy

from packetraven.base import PacketSource
from packetraven.connections import PacketDatabaseTable, PacketGeoJSON, TimeIntervalError
from packetraven.tracks import APRSTrack, LocationPacketTrack
from packetraven.utilities import get_logger
from packetraven.writer import write_packet_tracks

LOGGER = get_logger('packetraven')


def retrieve_packets(
    connections: [PacketSource],
    packet_tracks: [LocationPacketTrack],
    database: PacketDatabaseTable = None,
    output_filename: PathLike = None,
    start_date: datetime = None,
    end_date: datetime = None,
    logger: Logger = None,
) -> {str: APRSPacket}:
    if output_filename is not None:
        if not isinstance(output_filename, Path):
            output_filename = Path(output_filename)

    if logger is None:
        logger = LOGGER

    logger.debug(f'receiving packets from {len(connections)} source(s)')
    current_time = datetime.now()

    parsed_packets = []
    for connection in connections:
        try:
            connection_packets = connection.packets
            parsed_packets.extend(connection_packets)
        except ConnectionError as error:
            LOGGER.error(f'{connection.__class__.__name__} - {error}')
        except TimeIntervalError:
            pass

    logger.debug(f'received {len(parsed_packets)} packets')

    new_packets = {}
    if len(parsed_packets) > 0:
        updated_callsigns = set()
        for parsed_packet in parsed_packets:
            callsign = parsed_packet['callsign']

            if start_date is not None and parsed_packet.time <= start_date:
                continue
            if end_date is not None and parsed_packet.time >= end_date:
                continue

            if callsign not in packet_tracks:
                packet_tracks[callsign] = APRSTrack(callsign, [parsed_packet])
                logger.debug(f'started tracking callsign {callsign:8}')
            else:
                packet_track = packet_tracks[callsign]
                if parsed_packet not in packet_track:
                    packet_track.append(parsed_packet)
                else:
                    if database is None or parsed_packet.source != database.location:
                        logger.debug(f'skipping duplicate packet: {parsed_packet}')
                    continue

            if parsed_packet.source not in new_packets:
                new_packets[parsed_packet.source] = []
            new_packets[parsed_packet.source].append(parsed_packet)
            if callsign not in updated_callsigns:
                updated_callsigns.add(callsign)

        for source in new_packets:
            new_packets[source] = list(sorted(new_packets[source]))

        for source, packets in new_packets.items():
            logger.info(f'received {len(packets)} new packet(s) from {source}: {packets}')
            parsed_packets.extend(packets)

        if database is not None:
            for packets in new_packets.values():
                database.send(packets)

        updated_callsigns = sorted(updated_callsigns)
        for callsign in updated_callsigns:
            packet_track = packet_tracks[callsign]
            packet_time = datetime.utcfromtimestamp(
                (packet_track.times[-1] - numpy.datetime64('1970-01-01T00:00:00Z'))
                / numpy.timedelta64(1, 's')
            )

            message = ''
            try:
                coordinate_string = ', '.join(
                    f'{coordinate:.3f}°' for coordinate in packet_track.coordinates[-1, :2]
                )
                message += (
                    f'{callsign:8} #{len(packet_track)} ({coordinate_string}, {packet_track.coordinates[-1, 2]:.2f}m)'
                    f'; {(current_time - packet_time) / timedelta(seconds=1):.2f}s old'
                    f'; {packet_track.intervals[-1]:.2f}s since last packet'
                    f'; {packet_track.overground_distances[-1]:.2f}m distance over ground ({packet_track.ground_speeds[-1]:.2f}m/s), '
                    f'{packet_track.ascents[-1]:.2f}m ascent ({packet_track.ascent_rates[-1]:.2f}m/s)'
                )

                if packet_track.time_to_ground >= timedelta(seconds=0):
                    current_time_to_ground = packet_time + packet_track.time_to_ground - current_time
                    message += (
                        f'; {packet_track} descending from max altitude of {packet_track.coordinates[:, 2].max():.3f} m'
                        f'; {current_time_to_ground / timedelta(seconds=1):.2f} s to the ground'
                    )
            except Exception as error:
                LOGGER.exception(f'{error.__class__.__name__} - {error}')
            finally:
                logger.info(message)

            packet_track.sort()

        if output_filename is not None:
            write_packet_tracks(
                [packet_tracks[callsign] for callsign in updated_callsigns], output_filename
            )

    output_filename_index = None
    for index, connection in enumerate(connections):
        if isinstance(connection, PacketGeoJSON):
            output_filename_index = index
    if output_filename_index is not None:
        connections.pop(output_filename_index)

    return new_packets
