from datetime import datetime, timedelta
from logging import Logger
from os import PathLike

from aprslib.packets.base import APRSPacket

from packetraven import APRSDatabaseTable
from packetraven.connections import APRSPacketConnection, TimeIntervalError
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger
from packetraven.writer import write_aprs_packet_tracks

LOGGER = get_logger('packetraven')

PACKET_SEND_BUFFER = []


def retrieve_packets(connections: [APRSPacketConnection], packet_tracks: [APRSTrack], database: APRSDatabaseTable = None,
                     output_filename: PathLike = None, start_date: datetime = None, end_date: datetime = None,
                     logger: Logger = None) -> [APRSPacket]:
    if logger is None:
        logger = LOGGER

    logger.debug(f'receiving packets from {len(connections)} source(s)')

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

    if len(parsed_packets) > 0:
        updated_callsigns = set()
        new_packets = {}
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
            updated_callsigns.add(callsign)

        parsed_packets = []
        for source, packets in new_packets.items():
            logger.info(f'received {len(packets)} new packet(s) from {source}: {packets}')
            parsed_packets.extend(packets)

        parsed_packets = sorted(parsed_packets)
        updated_callsigns = sorted(updated_callsigns)

        if database is not None:
            new_packets = [packet for packet in parsed_packets if packet not in database]
            if len(PACKET_SEND_BUFFER) > 0:
                new_packets.extend(PACKET_SEND_BUFFER)
                PACKET_SEND_BUFFER.clear()
            if len(new_packets) > 0:
                logger.info(f'sending {len(new_packets)} packet(s) to {database.location}: {new_packets}')
                try:
                    database.insert(new_packets)
                except ConnectionError as error:
                    logger.info(f'could not send packet(s) ({error}); reattempting on next iteration')
                    PACKET_SEND_BUFFER.extend(new_packets)

        for callsign in updated_callsigns:
            packet_track = packet_tracks[callsign]
            coordinate_string = ', '.join(f'{coordinate:.3f}°' for coordinate in packet_track.coordinates[-1, :2])
            message = f'{callsign:8} #{len(packet_track)} ({coordinate_string}, {packet_track.coordinates[-1, 2]:.2f} m); ' \
                      f'{packet_track.intervals[-1]:.2f} s since last packet: ' \
                      f'{packet_track.distances[-1]:.2f} m distance over ground ({packet_track.ascent_rates[-1]:.2f} m/s), ' \
                      f'{packet_track.ascents[-1]:.2f} m ascent ({packet_track.ground_speeds[-1]:.2f} m/s)'

            if packet_track.time_to_ground >= timedelta(seconds=0):
                message += f'; currently falling from {packet_track.coordinates[:, 2].max():.3f} m; ' \
                           f'{packet_track.time_to_ground / timedelta(seconds=1):.2f} s to the ground'

            logger.info(message)

        if output_filename is not None:
            write_aprs_packet_tracks([packet_tracks[callsign] for callsign in updated_callsigns], output_filename)

    return parsed_packets
