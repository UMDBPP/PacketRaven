from packetraven import TextFileTNC
from packetraven.tracks import APRSTrack

if __name__ == '__main__':
    filename = 'http://bpp.umd.edu/archives/Launches/NS-95_2020-11-07/APRS/W3EAX-11/W3EAX-11_raw_NS95.txt'
    raw_packet_text_file = TextFileTNC(filename)

    packets = raw_packet_text_file.packets

    packet_track = APRSTrack(callsign='W3EAX-11', packets=packets)

    print(f'number of packets: {len(packet_track)}')
    print(f'time to ground: {packet_track.time_to_ground}')
    print(f'distance traveled (m): {packet_track.cumulative_overground_distances[-1]}')
    print(f'maximum altitude (m): {max(packet_track.altitudes)}')
