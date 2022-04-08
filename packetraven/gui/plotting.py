from tkinter import Toplevel
from typing import Dict

from matplotlib import pyplot
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from packetraven.packets.tracks import LocationPacketTrack, PredictedTrajectory

# import matplotlib
# matplotlib.use('TkAgg')
# matplotlib.interactive(True)

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


class LiveTrackPlot:
    """
    wrapper for a `matplotlib` plot window that can be updated on the fly with packet tracks
    """

    def __init__(
        self,
        packet_tracks: Dict[str, LocationPacketTrack],
        variable: str,
        predictions: Dict[str, PredictedTrajectory] = None,
    ):
        if variable not in VARIABLES:
            raise NotImplementedError(f'unsupported plotting variable "{variable}"')

        self.packet_tracks = packet_tracks
        self.predictions = predictions if predictions is not None else {}
        self.variable = variable

        try:
            self.window.protocol('WM_DELETE_WINDOW', self.window.iconify)
        except AttributeError:
            pass

        self.update()

    def update(
        self,
        packet_tracks: Dict[str, LocationPacketTrack] = None,
        predictions: Dict[str, PredictedTrajectory] = None,
    ):
        if packet_tracks is not None:
            self.packet_tracks.update(packet_tracks)
        if predictions is not None:
            self.predictions.update(predictions)

        if len(self.packet_tracks) > 0 or len(self.predictions) > 0:
            try:
                if self.window.state() == 'iconic':
                    self.window.deiconify()
                if self.window.focus_get() is None:
                    self.window.focus_force()
            except AttributeError:
                pass

            axis = self.axis

            while len(axis.lines) > 0:
                axis.lines.pop(-1)

            packet_track_lines = {}
            for name, packet_track in self.packet_tracks.items():
                x = getattr(packet_track, VARIABLES[self.variable]['x'])
                y = getattr(packet_track, VARIABLES[self.variable]['y'])
                lines = axis.plot(x, y, linewidth=2, marker='o', label=packet_track.name)
                packet_track_lines[name] = lines[0]

            for name, prediction in self.predictions.items():
                color = (
                    packet_track_lines[name].get_color()
                    if name in packet_track_lines
                    else None
                )
                x = getattr(prediction, VARIABLES[self.variable]['x'])
                y = getattr(prediction, VARIABLES[self.variable]['y'])
                axis.plot(
                    x,
                    y,
                    '--',
                    linewidth=0.5,
                    color=color,
                    label=f'{prediction.name} prediction',
                )

            axis.legend()

            # NOTE: this `pyplot.pause(0.1)` NEEDS to be here, and it NEEDS to be `0.1` seconds per track;
            # otherwise the plot does not render correctly upon update
            pyplot.pause(0.1 * (len(self.packet_tracks) + len(self.predictions)))

    @property
    def window(self) -> Toplevel:
        return self.figure.canvas.manager.window

    @property
    def figure(self) -> Figure:
        if not hasattr(self, '__figure') or not pyplot.fignum_exists(self.__figure.number):
            self.__figure = self.__new_figure()
        return self.__figure

    @property
    def axis(self) -> Axes:
        if not hasattr(self, '__axis') or self.__axis.figure is not self.figure:
            self.__axis = self.__new_axis()
        return self.__axis

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
