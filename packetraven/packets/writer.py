from os import PathLike
from pathlib import Path
from typing import List

import geojson
from geojson import Point
import numpy
from shapely.geometry import LineString
import typepigeon

from packetraven.packets import APRSPacket
from packetraven.packets.tracks import APRSTrack, LocationPacketTrack, PredictedTrajectory

KML_STANDARD = '{http://www.opengis.net/kml/2.2}'


def write_packet_tracks(packet_tracks: List[LocationPacketTrack], filename: PathLike):
    """
    write packet tracks to file
    """

    if not isinstance(filename, Path):
        filename = Path(filename)
    if filename.suffix == '.txt':
        packets = []
        for packet_track_index, packet_track in enumerate(packet_tracks):
            packets.extend(packet_track)
        packets = sorted(packets)
        lines = [
            f'{packet.time:%Y-%m-%d %H:%M:%S %Z}: {packet.frame}'
            if isinstance(packet, APRSPacket)
            else f'{packet.time:%Y-%m-%d %H:%M:%S %Z}'
            for packet in packets
        ]
        with open(filename, 'w') as output_file:
            output_file.write('\n'.join(lines))
    elif filename.suffix in ['.geojson', '.json']:
        features = []
        for packet_track in packet_tracks:
            ascent_rates = numpy.round(packet_track.ascent_rates, 3)
            ground_speeds = numpy.round(packet_track.ground_speeds, 3)

            for packet_index, packet in enumerate(packet_track):
                properties = {
                    'time': f'{packet.time:%Y%m%d%H%M%S}',
                    'altitude': float(packet.coordinates[2]),
                    'ascent_rate': float(ascent_rates[packet_index]),
                    'ground_speed': float(ground_speeds[packet_index]),
                }

                properties.update(packet.attributes)

                features.append(
                    geojson.Feature(
                        geometry=geojson.Point(packet.coordinates.tolist()),
                        properties=properties,
                    )
                )

            properties = {
                'name': packet_track.name,
                'start_time': f'{packet_track.packets[0].time:%Y-%m-%d %H:%M:%S}',
                'end_time': f'{packet_track.packets[-1].time:%Y-%m-%d %H:%M:%S}',
                'duration': f'{packet_track.packets[-1].time - packet_track.packets[0].time}',
                **packet_track.attributes,
            }

            if isinstance(packet_track, PredictedTrajectory):
                properties.update(
                    {**packet_track.metadata, **packet_track.parameters,}
                )
            else:
                properties.update(
                    {
                        'seconds_to_ground': packet_track.time_to_ground,
                        'last_altitude': float(packet_track.coordinates[-1, -1]),
                        'last_ascent_rate': float(ascent_rates[-1]),
                        'last_ground_speed': float(ground_speeds[-1]),
                    }
                )

            features.append(
                geojson.Feature(
                    geometry=geojson.LineString(
                        [packet.coordinates.tolist() for packet in packet_track.packets]
                    ),
                    properties=typepigeon.convert_to_json(properties),
                )
            )

        features = geojson.FeatureCollection(features)

        with open(filename, 'w') as output_file:
            geojson.dump(features, output_file)
    elif filename.suffix == '.kml':
        from fastkml import kml

        output_kml = kml.KML()
        document = kml.Document(
            KML_STANDARD, '1', 'root document', 'root document, containing geometries'
        )
        output_kml.append(document)

        for packet_track_index, packet_track in enumerate(packet_tracks):
            ascent_rates = numpy.round(packet_track.ascent_rates, 3)
            ground_speeds = numpy.round(packet_track.ground_speeds, 3)

            for packet_index, packet in enumerate(packet_track):
                placemark = kml.Placemark(
                    KML_STANDARD,
                    f'1 {packet_track_index} {packet_index}',
                    f'{packet.time:%Y%m%d%H%M%S} {packet_track.callsign if isinstance(packet_track, APRSTrack) else ""}',
                    f'altitude={packet.coordinates[2]} '
                    f'ascent_rate={ascent_rates[packet_index]} '
                    f'ground_speed={ground_speeds[packet_index]}',
                )
                placemark.geometry = Point(packet.coordinates.tolist())
                document.append(placemark)

            properties = {
                'altitude': packet_track.coordinates[-1, -1],
                'duration': f'{packet_track.packets[-1].time - packet_track.packets[0].time}',
            }

            if isinstance(packet_track, PredictedTrajectory):
                properties.update(
                    {**packet_track.metadata, **packet_track.parameters,}
                )
            else:
                properties.update(
                    {
                        'seconds_to_ground': packet_track.time_to_ground,
                        'last_altitude': float(packet_track.coordinates[-1, -1]),
                        'last_ascent_rate': float(ascent_rates[-1]),
                        'last_ground_speed': float(ground_speeds[-1]),
                    }
                )

            properties = ' '.join(f'{key}={value}' for key, value in properties.items())

            placemark = kml.Placemark(
                KML_STANDARD, f'1 {packet_track_index}', packet_track.name, properties,
            )
            placemark.geometry = LineString(packet_track.coordinates)
            document.append(placemark)

        with open(filename, 'w') as output_file:
            output_file.write(output_kml.to_string())
    else:
        raise NotImplementedError(
            f'saving to file type "{filename.suffix}" has not been implemented'
        )
