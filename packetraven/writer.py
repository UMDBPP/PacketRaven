from datetime import timedelta
from os import PathLike
from pathlib import Path

from geojson import Point
from shapely.geometry import LineString

from .tracks import APRSTrack

KML_STANDARD = '{http://www.opengis.net/kml/2.2}'


def write_aprs_packet_tracks(packet_tracks: [APRSTrack], output_filename: PathLike):
    if not isinstance(output_filename, Path):
        output_filename = Path(output_filename)
    output_filename = output_filename.resolve().expanduser()
    extension = output_filename.suffix
    if extension == '.geojson':
        import geojson

        features = []
        for packet_track in packet_tracks:
            features.extend(geojson.Feature(geometry=geojson.Point(packet.coordinates.tolist()),
                                            properties={
                                                'time'        : f'{packet.time:%Y%m%d%H%M%S}',
                                                'callsign'    : packet.callsign,
                                                'altitude'    : packet.coordinates[2],
                                                'ascent_rate' : packet_track.ascent_rates[packet_index],
                                                'ground_speed': packet_track.ground_speeds[packet_index]
                                            })
                            for packet_index, packet in enumerate(packet_track))

            features.append(geojson.Feature(geometry=geojson.LineString([packet.coordinates.tolist()
                                                                         for packet in packet_track.packets]),
                                            properties={
                                                'time'             : f'{packet_track.packets[-1].time:%Y%m%d%H%M%S}',
                                                'callsign'         : packet_track.callsign,
                                                'altitude'         : packet_track.coordinates[-1, -1],
                                                'ascent_rate'      : packet_track.ascent_rates[-1],
                                                'ground_speed'     : packet_track.ground_speeds[-1],
                                                'seconds_to_ground': packet_track.time_to_ground / timedelta(seconds=1)
                                            }))

        features = geojson.FeatureCollection(features)

        with open(output_filename, 'w') as output_file:
            geojson.dump(features, output_file)
    elif extension == '.kml':
        from fastkml import kml

        output_kml = kml.KML()
        document = kml.Document(KML_STANDARD, '1', 'root document', 'root document, containing geometries')
        output_kml.append(document)

        for packet_track_index, packet_track in enumerate(packet_tracks):
            for packet_index, packet in enumerate(packet_track):
                placemark = kml.Placemark(KML_STANDARD, f'1 {packet_track_index} {packet_index}',
                                          f'{packet_track.callsign} {packet.time:%Y%m%d%H%M%S}',
                                          f'altitude={packet.coordinates[2]} '
                                          f'ascent_rate={packet_track.ascent_rates[packet_index]} '
                                          f'ground_speed={packet_track.ground_speeds[packet_index]}')
                placemark.geometry = Point(packet.coordinates.tolist())
                document.append(placemark)

            placemark = kml.Placemark(KML_STANDARD, f'1 {packet_track_index}', packet_track.callsign,
                                      f'altitude={packet_track.coordinates[-1, -1]} '
                                      f'ascent_rate={packet_track.ascent_rates[-1]} '
                                      f'ground_speed={packet_track.ground_speeds[-1]} '
                                      f'seconds_to_ground={packet_track.time_to_ground / timedelta(seconds=1)}')
            placemark.geometry = LineString(packet_track.coordinates)
            document.append(placemark)

        with open(output_filename, 'w') as output_file:
            output_file.write(output_kml.to_string())
    else:
        raise NotImplementedError(f'saving to file type "{extension}" has not been implemented')
