from datetime import datetime
from logging import Logger
from os import PathLike

from aprslib.packets.base import APRSPacket

from packetraven import APRSPacketDatabaseTable
from packetraven.connections import APRSPacketConnection
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger
from packetraven.writer import write_aprs_packet_tracks

LOGGER = get_logger('packetraven')


def retrieve_packets(connections: [APRSPacketConnection], packet_tracks: [APRSTrack], database: APRSPacketDatabaseTable = None,
                     output_filename: PathLike = None, start_date: datetime = None, end_date: datetime = None,
                     logger: Logger = None) -> [APRSPacket]:
    if logger is None:
        logger = LOGGER

    logger.debug(f'receiving packets from {len(connections)} source(s)')

    parsed_packets = []
    for connection in connections:
        parsed_packets.extend(connection.packets)

    logger.debug(f'received {len(parsed_packets)} packets')

    if len(parsed_packets) > 0:
        updated_callsigns = set()
        new_packets = {}
        for parsed_packet in parsed_packets:
            callsign = parsed_packet['callsign']

            if start_date is not None and parsed_packet.times <= start_date:
                continue
            if end_date is not None and parsed_packet.times >= end_date:
                continue

            if callsign not in packet_tracks:
                packet_tracks[callsign] = APRSTrack(callsign, [parsed_packet])
                logger.debug(f'started tracking {callsign:8}')
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
            if len(new_packets) > 0:
                logger.info(f'sending {len(new_packets)} packet(s) to {database.location}')
                database.insert(new_packets)

        for callsign in updated_callsigns:
            ascent_rate = packet_tracks[callsign].ascent_rates[-1]
            ground_speed = packet_tracks[callsign].ground_speeds[-1]
            seconds_to_impact = packet_tracks[callsign].seconds_to_impact
            logger.info(f'{callsign:8} ascent rate      : {ascent_rate} m/s')
            logger.info(f'{callsign:8} ground speed     : {ground_speed} m/s')
            if seconds_to_impact >= 0:
                logger.info(f'{callsign:8} estimated landing: {seconds_to_impact} s')

        if output_filename is not None:
            write_aprs_packet_tracks([packet_tracks[callsign] for callsign in updated_callsigns], output_filename)

    return parsed_packets
