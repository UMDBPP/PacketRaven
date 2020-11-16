from matplotlib import pyplot

from packetraven.tracks import LocationPacketTrack

VARIABLES = {
    'altitude': {'x': 'cumulative_overground_distances', 'y': 'altitudes', 'xlabel': 'overground distance (m)', 'ylabel': 'altitude (m)'},
    'ascent_rate': {'x': 'times', 'y': 'ascent_rates', 'xlabel': 'time', 'ylabel': 'ascent rate (m/s)'},
    'ground_speed': {'x': 'altitudes', 'y': 'ground_speeds', 'xlabel': 'altitude (m)', 'ylabel': 'ground speed (m/s)'}
}


class LivePlot:
    def __init__(self, packet_tracks: {str: LocationPacketTrack}, variable: str, show: bool = True):
        if variable not in VARIABLES:
            raise NotImplementedError(f'unsupported plotting variable "{variable}"')

        self.packet_tracks = packet_tracks
        self.variable = variable

        self.figure = pyplot.figure()
        self.figure_id = self.figure.number
        self.axis = self.figure.add_subplot(1, 1, 1)

        self.axis.set_xlabel(VARIABLES[self.variable]['xlabel'])
        self.axis.set_ylabel(VARIABLES[self.variable]['ylabel'])

        for name, packet_track in self.packet_tracks.items():
            self.axis.plot(
                getattr(packet_track, VARIABLES[self.variable]['x']),
                getattr(packet_track, VARIABLES[self.variable]['y']),
                label=packet_track.name,
            )

        if show:
            pyplot.show(block=False)

    def update(self, packet_tracks: {str: LocationPacketTrack}):
        self.packet_tracks.update(packet_tracks)
        self.axis.clear()

        if not pyplot.fignum_exists(self.figure_id):
            self.figure = pyplot.figure()
            self.figure_id = self.figure.number
            self.axis = self.figure.add_subplot(1, 1, 1)

        for name, packet_track in self.packet_tracks.items():
            self.axis.plot(
                getattr(packet_track, VARIABLES[self.variable]['x']),
                getattr(packet_track, VARIABLES[self.variable]['y']),
                label=packet_track.name,
            )

        pyplot.draw()

    def close(self):
        pyplot.close(self.figure_id)
