from tkinter import Toplevel

from matplotlib import pyplot
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from packetraven.tracks import LocationPacketTrack

VARIABLES = {
    'altitude': {'x': 'times', 'y': 'altitudes', 'xlabel': 'time', 'ylabel': 'altitude (m)'},
    'ascent_rate': {
        'x': 'times',
        'y': 'ascent_rates',
        'xlabel': 'time',
        'ylabel': 'ascent rate (m/s)',
    },
    'ground_speed': {
        'x': 'ground_speeds',
        'y': 'altitudes',
        'xlabel': 'ground speed (m/s)',
        'ylabel': 'altitude (m)',
    },
}


class LivePlot:
    def __init__(self, packet_tracks: {str: LocationPacketTrack}, variable: str):
        if variable not in VARIABLES:
            raise NotImplementedError(f'unsupported plotting variable "{variable}"')

        self.packet_tracks = packet_tracks
        self.variable = variable

        self.window.protocol('WM_DELETE_WINDOW', self.window.iconify)

        self.update()

    def update(self, packet_tracks: {str: LocationPacketTrack} = None):
        if packet_tracks is not None:
            self.packet_tracks.update(packet_tracks)

        if len(self.packet_tracks) > 0:
            if self.window.state() == 'iconic':
                self.window.deiconify()
            if self.window.focus_get() is None:
                self.window.focus_force()

            while len(self.axis.lines) > 0:
                self.axis.lines.pop(-1)

            for name, packet_track in self.packet_tracks.items():
                self.axis.scatter(
                    getattr(packet_track, VARIABLES[self.variable]['x']),
                    getattr(packet_track, VARIABLES[self.variable]['y']),
                    label=packet_track.name,
                    s=2,
                )

            self.axis.legend()
            pyplot.draw()

    @property
    def window(self) -> Toplevel:
        return self.figure.canvas.manager.window

    @property
    def figure(self) -> Figure:
        try:
            figure = self.__figure
            if not pyplot.fignum_exists(figure.number):
                raise RuntimeError
        except (AttributeError, RuntimeError):
            figure = self.__new_figure()
        self.__figure = figure
        pyplot.show(block=False)
        return figure

    @property
    def axis(self) -> Axes:
        try:
            axis = self.__axis
            figure = axis.figure
            if figure is not self.figure:
                raise RuntimeError
        except (AttributeError, RuntimeError):
            axis = self.__new_axis()
        self.__axis = axis
        return axis

    def __new_figure(self) -> Figure:
        x_label = VARIABLES[self.variable]['xlabel']
        y_label = VARIABLES[self.variable]['ylabel']

        return pyplot.figure(num=f'{y_label} / {x_label}')

    def __new_axis(self, figure: Figure = None) -> Axes:
        if figure is None:
            figure = self.figure

        x_label = VARIABLES[self.variable]['xlabel']
        y_label = VARIABLES[self.variable]['ylabel']

        axis = figure.add_subplot(1, 1, 1)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)

        return axis

    def close(self):
        pyplot.close(self.figure.number)
