from datetime import datetime, timedelta
import logging
from os import PathLike
from pathlib import Path
import re
import sys
import tkinter
from tkinter import filedialog, messagebox, simpledialog
from tkinter.ttk import Combobox, Separator
from typing import Callable, Collection

from aprslib.packets.base import APRSPacket
from dateutil.parser import parse
import numpy

from packetraven import APRSDatabaseTable, APRSfi, RawAPRSTextFile, SerialTNC
from packetraven.__main__ import DEFAULT_INTERVAL_SECONDS, LOGGER, retrieve_packets
from packetraven.base import available_serial_ports, next_open_serial_port
from packetraven.connections import APRSis, PacketGeoJSON
from packetraven.plotting import LivePlot
from packetraven.predicts import PredictionError, get_predictions
from packetraven.tracks import LocationPacketTrack, PredictedTrajectory
from packetraven.utilities import get_logger
from packetraven.writer import write_packet_tracks


class PacketRavenGUI:
    def __init__(
        self,
        callsigns: [str] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        log_filename: PathLike = None,
        output_filename: PathLike = None,
        prediction_filename: PathLike = None,
        interval_seconds: int = None,
        igate: bool = False,
        **kwargs,
    ):
        main_window = tkinter.Tk()
        main_window.title('PacketRaven')
        self.__windows = {'main': main_window}

        self.interval_seconds = (
            interval_seconds if interval_seconds is not None else DEFAULT_INTERVAL_SECONDS
        )

        self.__configuration = {
            'aprs_fi': {'aprs_fi_key': None},
            'tnc': {'tnc': None},
            'database': {
                'database_hostname': None,
                'database_database': None,
                'database_table': None,
                'database_username': None,
                'database_password': None,
            },
            'ssh_tunnel': {'ssh_hostname': None, 'ssh_username': None, 'ssh_password': None},
            'prediction': {
                'prediction_ascent_rate': None,
                'prediction_burst_altitude': None,
                'prediction_sea_level_descent_rate': None,
                'prediction_float_altitude': None,
                'prediction_float_duration': None,
                'prediction_api_url': None,
            },
        }

        for section_name, section in self.__configuration.items():
            section.update({key: value for key, value in kwargs.items() if key in section})

        self.igate = igate

        self.database = None
        self.aprs_is = None
        self.__connections = []

        self.__running = False
        self.__toggles = {}
        self.__packet_tracks = {}

        self.__frames = {}
        self.__elements = {}

        self.__plots = {}

        configuration_frame = tkinter.Frame(main_window)
        configuration_frame.grid(row=main_window.grid_size()[1], column=0, pady=10)
        self.__frames['configuration'] = configuration_frame

        start_date_entry = self.__add_entry_box(
            configuration_frame, title='start_date', label='Start Date', width=22, sticky='w',
        )
        self.__add_entry_box(
            configuration_frame,
            title='end_date',
            label='End Date',
            width=22,
            row=start_date_entry.grid_info()['row'],
            column=start_date_entry.grid_info()['column'] + 1,
            sticky='e',
        )

        separator = Separator(configuration_frame, orient=tkinter.HORIZONTAL)
        separator.grid(
            row=configuration_frame.grid_size()[1],
            column=0,
            columnspan=configuration_frame.grid_size()[0] + 1,
            sticky='ew',
            pady=10,
        )

        self.__add_entry_box(
            configuration_frame,
            title='callsigns',
            label='Callsigns',
            width=63,
            columnspan=configuration_frame.grid_size()[0],
        )
        self.__file_selection_option = 'select file...'
        self.__add_combo_box(
            configuration_frame,
            title='tnc',
            label='TNC',
            options=list(available_serial_ports()) + [self.__file_selection_option],
            option_select=self.__select_tnc,
            width=60,
            columnspan=configuration_frame.grid_size()[0],
            sticky='w',
        )

        separator = Separator(configuration_frame, orient=tkinter.HORIZONTAL)
        separator.grid(
            row=configuration_frame.grid_size()[1],
            column=0,
            columnspan=configuration_frame.grid_size()[0] + 1,
            sticky='ew',
            pady=10,
        )

        log_file_label = tkinter.Label(configuration_frame, text='Log')
        log_file_label.grid(row=configuration_frame.grid_size()[1], column=0, sticky='w')

        log_file_frame = tkinter.Frame(configuration_frame)
        log_file_frame.grid(
            row=log_file_label.grid_info()['row'],
            column=1,
            columnspan=configuration_frame.grid_size()[0] - 1,
        )

        self.__toggles['log_file'] = tkinter.BooleanVar()
        log_file_checkbox = tkinter.Checkbutton(
            log_file_frame, variable=self.__toggles['log_file'], command=self.__toggle_log_file
        )
        log_file_checkbox.grid(row=0, column=0, padx=10)
        if log_filename is not None:
            log_file_checkbox.select()

        self.__elements['log_file_box'] = self.__add_file_box(
            log_file_frame,
            row=0,
            column=1,
            title='log_file',
            file_select=self.__select_log_file,
            width=52,
            sticky='w',
        )

        output_file_label = tkinter.Label(configuration_frame, text='Output')
        output_file_label.grid(row=configuration_frame.grid_size()[1], column=0, sticky='w')

        output_file_frame = tkinter.Frame(configuration_frame)
        output_file_frame.grid(
            row=output_file_label.grid_info()['row'],
            column=1,
            columnspan=configuration_frame.grid_size()[0] - 1,
        )

        self.__toggles['output_file'] = tkinter.BooleanVar()
        output_file_checkbox = tkinter.Checkbutton(
            output_file_frame,
            variable=self.__toggles['output_file'],
            command=self.__toggle_output_file,
        )
        output_file_checkbox.grid(row=0, column=0, padx=10)
        if output_filename is not None:
            output_file_checkbox.select()

        self.__elements['output_file_box'] = self.__add_file_box(
            output_file_frame,
            row=0,
            column=1,
            title='output_file',
            file_select=self.__select_output_file,
            width=52,
            sticky='w',
        )

        separator = Separator(configuration_frame, orient=tkinter.HORIZONTAL)
        separator.grid(
            row=configuration_frame.grid_size()[1],
            column=0,
            columnspan=configuration_frame.grid_size()[0] + 1,
            sticky='ew',
            pady=10,
        )

        prediction_label = tkinter.Label(configuration_frame, text='Predict')
        prediction_label.grid(row=configuration_frame.grid_size()[1], column=0, sticky='w')

        prediction_frame = tkinter.Frame(configuration_frame)
        prediction_frame.grid(
            row=prediction_label.grid_info()['row'],
            column=1,
            columnspan=configuration_frame.grid_size()[0] - 1,
        )

        self.__toggles['prediction_file'] = tkinter.BooleanVar()
        prediction_checkbox = tkinter.Checkbutton(
            prediction_frame,
            variable=self.__toggles['prediction_file'],
            command=self.__toggle_prediction_file,
        )
        prediction_checkbox.grid(row=0, column=0, padx=10)
        if prediction_filename is not None:
            prediction_checkbox.select()

        self.__elements['prediction_file_box'] = self.__add_file_box(
            prediction_frame,
            row=0,
            column=1,
            title='prediction_file',
            file_select=self.__select_prediction_file,
            width=52,
            sticky='w',
        )

        separator = Separator(configuration_frame, orient=tkinter.HORIZONTAL)
        separator.grid(
            row=configuration_frame.grid_size()[1],
            column=0,
            columnspan=configuration_frame.grid_size()[0] + 1,
            sticky='ew',
            pady=10,
        )

        plot_label = tkinter.Label(configuration_frame, text='Plots')
        plot_label.grid(row=configuration_frame.grid_size()[1], column=0, sticky='w')

        plot_checkbox_frame = tkinter.Frame(configuration_frame)
        plot_checkbox_frame.grid(
            row=plot_label.grid_info()['row'],
            column=0,
            columnspan=configuration_frame.grid_size()[0] - 1,
        )

        plot_variables = ['altitude', 'ascent_rate', 'ground_speed']
        self.__plot_toggles = {}
        for plot_index, plot in enumerate(plot_variables):
            boolean_var = tkinter.BooleanVar()
            plot_checkbox = tkinter.Checkbutton(
                plot_checkbox_frame, text=plot, variable=boolean_var
            )
            plot_checkbox.grid(row=0, column=plot_index, padx=10)
            self.__plot_toggles[plot] = boolean_var

        separator = Separator(main_window, orient=tkinter.HORIZONTAL)
        separator.grid(row=main_window.grid_size()[1], column=0, sticky='ew')

        control_frame = tkinter.Frame(main_window)
        control_frame.grid(row=main_window.grid_size()[1], column=0, pady=10)
        self.__frames['controls'] = control_frame

        self.__toggle_text = tkinter.StringVar()
        self.__toggle_text.set('Start')
        toggle_button = tkinter.Button(
            control_frame, textvariable=self.__toggle_text, command=self.toggle
        )
        toggle_button.grid(row=control_frame.grid_size()[1], column=0, sticky='nsew')

        self.callsigns = callsigns
        self.tncs = self.__configuration['tnc']['tnc']

        if start_date is not None:
            self.start_date = start_date
        if end_date is not None:
            self.end_date = end_date

        self.log_filename = log_filename
        if self.log_filename is None:
            self.log_filename = Path('~') / 'Desktop'
        self.__toggle_log_file()

        self.output_filename = output_filename
        if self.output_filename is None:
            self.output_filename = Path('~') / 'Desktop'
        self.__toggle_output_file()

        self.prediction_filename = prediction_filename
        if self.prediction_filename is None:
            self.prediction_filename = Path('~') / 'Desktop'
        self.__toggle_prediction_file()
        self.__predictions = {}

        self.__windows['main'].protocol('WM_DELETE_WINDOW', self.close)

        main_window.mainloop()

    @property
    def callsigns(self) -> [str]:
        callsigns = self.__elements['callsigns'].get()
        if len(callsigns) > 0:
            callsigns = [
                callsign.strip().upper()
                for callsign in re.split(',+\ *|\ +', callsigns.strip('"'))
            ]
        else:
            callsigns = None
        self.callsigns = callsigns
        return callsigns

    @callsigns.setter
    def callsigns(self, callsigns: [str]):
        if callsigns is not None:
            callsigns = ', '.join([callsign.upper() for callsign in callsigns])
        else:
            callsigns = ''
        self.replace_text(self.__elements['callsigns'], callsigns)

    @property
    def tncs(self) -> [str]:
        """ locations of TNCs parsing APRS audio into ASCII frames """
        tncs = []
        for tnc in self.__elements['tnc'].get().split(','):
            tnc = tnc.strip()
            if len(tnc) > 0:
                if tnc.upper() == 'AUTO':
                    try:
                        tnc = next_open_serial_port()
                    except OSError:
                        LOGGER.warning(f'no open serial ports')
                        tnc = None
                tncs.append(tnc)
        return tncs

    @tncs.setter
    def tncs(self, filenames: [PathLike]):
        if filenames is None:
            filenames = []
        elif not isinstance(filenames, Collection) or isinstance(filenames, str):
            filenames = [filenames]

        filenames = [str(filename) for filename in filenames]

        self.__configuration['tnc']['tnc'] = filenames
        self.replace_text(self.__elements['tnc'], ', '.join(filenames))

    @property
    def start_date(self) -> datetime:
        start_date = self.__elements['start_date'].get()
        if len(start_date) > 0:
            start_date = parse(start_date)
        else:
            start_date = None
        return start_date

    @start_date.setter
    def start_date(self, start_date: datetime):
        if start_date is not None:
            if isinstance(start_date, str):
                start_date = parse(start_date)
            start_date = f'{start_date:%Y-%m-%d %H:%M:%S}'
        else:
            start_date = ''
        self.replace_text(self.__elements['start_date'], start_date)

    @property
    def end_date(self) -> datetime:
        end_date = self.__elements['end_date'].get()
        if len(end_date) > 0:
            end_date = parse(end_date)
        else:
            end_date = None
        return end_date

    @end_date.setter
    def end_date(self, end_date: datetime):
        if end_date is not None:
            if isinstance(end_date, str):
                end_date = parse(end_date)
            end_date = f'{end_date:%Y-%m-%d %H:%M:%S}'
        else:
            end_date = ''
        self.replace_text(self.__elements['end_date'], end_date)

    @property
    def log_filename(self) -> Path:
        if self.toggles['log_file']:
            filename = self.__elements['log_file'].get()
            if len(filename) > 0:
                filename = Path(filename)
                if filename.expanduser().resolve().is_dir():
                    self.log_filename = filename
                    filename = self.log_filename
            else:
                filename = None
        else:
            filename = None
        return filename

    @log_filename.setter
    def log_filename(self, filename: PathLike):
        if filename is not None:
            if not isinstance(filename, Path):
                filename = Path(filename)
            if filename.expanduser().resolve().is_dir():
                filename = filename / f'packetraven_log_{datetime.now():%Y%m%dT%H%M%S}.txt'
        else:
            filename = ''
        self.replace_text(self.__elements['log_file'], filename)

    @property
    def output_filename(self) -> Path:
        if self.toggles['output_file']:
            filename = self.__elements['output_file'].get()
            if len(filename) > 0:
                filename = Path(filename)
                if filename.expanduser().resolve().is_dir():
                    self.output_filename = filename
                    filename = self.output_filename
            else:
                filename = None
        else:
            filename = None
        return filename

    @output_filename.setter
    def output_filename(self, filename: PathLike):
        if filename is not None:
            if not isinstance(filename, Path):
                filename = Path(filename)
            if filename.expanduser().resolve().is_dir():
                filename = (
                    filename / f'packetraven_output_{datetime.now():%Y%m%dT%H%M%S}.geojson'
                )
        else:
            filename = ''
        self.replace_text(self.__elements['output_file'], filename)

    @property
    def prediction_filename(self) -> Path:
        if self.toggles['prediction_file']:
            filename = self.__elements['prediction_file'].get()
            if len(filename) > 0:
                filename = Path(filename)
                if filename.expanduser().resolve().is_dir():
                    self.prediction_filename = filename
                    filename = self.prediction_filename
            else:
                filename = None
        else:
            filename = None
        return filename

    @prediction_filename.setter
    def prediction_filename(self, filename: PathLike):
        if filename is not None:
            if not isinstance(filename, Path):
                filename = Path(filename)
            if filename.expanduser().resolve().is_dir():
                filename = (
                    filename / f'packetraven_predict_{datetime.now():%Y%m%dT%H%M%S}.geojson'
                )
        else:
            filename = ''
        self.replace_text(self.__elements['prediction_file'], filename)

    @property
    def toggles(self) -> {str: bool}:
        return {key: value.get() for key, value in self.__toggles.items()}

    @property
    def running(self) -> bool:
        return self.__running

    @running.setter
    def running(self, running: bool):
        if running is not self.running:
            self.toggle()

    @property
    def packet_tracks(self) -> {str: LocationPacketTrack}:
        return self.__packet_tracks

    @property
    def predictions(self) -> {str: PredictedTrajectory}:
        return self.__predictions if self.toggles['prediction_file'] else None

    def __select_tnc(self, event):
        if event.widget.get() == self.__file_selection_option:
            self.tncs = filedialog.askopenfilename(
                title='Select TNC text file...',
                defaultextension='.txt',
                filetypes=[('Text', '*.txt')],
            )

    def __select_log_file(self):
        self.log_filename = filedialog.asksaveasfilename(
            title='Create log file...',
            initialdir=self.log_filename.parent,
            initialfile=self.log_filename.stem,
            defaultextension='.txt',
            filetypes=[('Text', '*.txt')],
        )

    def __select_output_file(self):
        self.output_filename = filedialog.asksaveasfilename(
            title='Create output file...',
            initialdir=self.output_filename.parent,
            initialfile=self.output_filename.stem,
            defaultextension='.geojson',
            filetypes=[
                ('GeoJSON', '*.geojson'),
                ('Text', '*.txt'),
                ('Keyhole Markup Language', '*.kml'),
            ],
        )

    def __select_prediction_file(self):
        self.prediction_filename = filedialog.asksaveasfilename(
            title='Create predict file...',
            initialdir=self.prediction_filename.parent,
            initialfile=self.prediction_filename.stem,
            defaultextension='.geojson',
            filetypes=[
                ('GeoJSON', '*.geojson'),
                ('Text', '*.txt'),
                ('Keyhole Markup Language', '*.kml'),
            ],
        )

    def __toggle_log_file(self):
        if self.toggles['log_file']:
            set_child_states(self.__elements['log_file_box'], state=tkinter.NORMAL)
            get_logger(LOGGER.name, log_filename=self.log_filename)
        else:
            set_child_states(self.__elements['log_file_box'], state=tkinter.DISABLED)
            for existing_file_handler in [
                handler for handler in LOGGER.handlers if type(handler) is logging.FileHandler
            ]:
                LOGGER.removeHandler(existing_file_handler)

    def __toggle_output_file(self):
        if self.toggles['output_file']:
            set_child_states(self.__elements['output_file_box'], state=tkinter.NORMAL)
        else:
            set_child_states(self.__elements['output_file_box'], state=tkinter.DISABLED)

    def __toggle_prediction_file(self):
        if self.toggles['prediction_file']:
            set_child_states(self.__elements['prediction_file_box'], state=tkinter.NORMAL)
        else:
            set_child_states(self.__elements['prediction_file_box'], state=tkinter.DISABLED)

    def __add_combo_box(
        self,
        frame: tkinter.Frame,
        title: str,
        options: [str],
        option_select: Callable = None,
        **kwargs,
    ) -> Combobox:
        width = kwargs['width'] if 'width' in kwargs else None
        combo_box = Combobox(frame, width=width)
        combo_box['values'] = options
        if option_select is not None:
            combo_box.bind('<<ComboboxSelected>>', option_select)
        return self.__add_text_box(frame, title, text_box=combo_box, **kwargs)

    def __add_file_box(
        self, frame: tkinter.Frame, title: str, file_select: Callable, **kwargs
    ) -> tkinter.Frame:
        if 'row' not in kwargs:
            kwargs['row'] = frame.grid_size()[1]
        if 'column' not in kwargs:
            kwargs['column'] = 0
        file_box_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in ['row', 'column', 'columnspan']
        }
        if 'columnspan' in file_box_kwargs:
            file_box_kwargs['columnspan'] -= 1

        if 'label' in kwargs:
            text_label = tkinter.Label(frame, text=kwargs['label'])
            text_label.grid(row=kwargs['row'], column=kwargs['column'], sticky='w')
            file_box_kwargs['column'] += 1

        file_box_frame = tkinter.Frame(frame)
        file_box_frame.grid(**file_box_kwargs)

        file_box = tkinter.Entry(
            file_box_frame, width=kwargs['width'] if 'width' in kwargs else None
        )
        file_button = tkinter.Button(file_box_frame, text='...', command=file_select)

        file_box.pack(side='left')
        file_button.pack(side='left')

        self.__elements[title] = file_box
        return file_box_frame

    def __add_entry_box(self, frame: tkinter.Frame, title: str, **kwargs) -> tkinter.Entry:
        if 'text_box' not in kwargs:
            kwargs['text_box'] = tkinter.Entry(
                frame, width=kwargs['width'] if 'width' in kwargs else None
            )
        return self.__add_text_box(frame, title, **kwargs)

    def __add_text_box(
        self,
        frame: tkinter.Frame,
        title: str,
        label: str,
        units: str = None,
        row: int = None,
        column: int = None,
        width: int = 10,
        text_box: tkinter.Entry = None,
        **kwargs,
    ) -> tkinter.Text:
        if row is None:
            row = frame.grid_size()[1]
        if column is None:
            column = 0

        if 'columnspan' in kwargs:
            if label is not None:
                kwargs['columnspan'] -= 1
            if units is not None:
                kwargs['columnspan'] -= 1

        if label is not None:
            text_label = tkinter.Label(frame, text=label)
            text_label.grid(row=row, column=column, sticky='w')
            column += 1

        if text_box is None:
            text_box = tkinter.Text(frame, width=width, height=1)
        text_box.grid(row=row, column=column, **kwargs)
        column += 1

        if units is not None:
            units_label = tkinter.Label(frame, text=units)
            units_label.grid(row=row, column=column)
            column += 1

        self.__elements[title] = text_box
        return text_box

    def toggle(self):
        if not self.running:
            if self.log_filename is not None:
                get_logger(LOGGER.name, self.log_filename)

            if self.toggles['log_file']:
                set_child_states(self.__elements['log_file_box'], tkinter.DISABLED)

            start_date = self.start_date
            self.__elements['start_date'].configure(state=tkinter.DISABLED)

            end_date = self.end_date
            self.__elements['end_date'].configure(state=tkinter.DISABLED)

            callsigns = self.callsigns
            self.__elements['callsigns'].configure(state=tkinter.DISABLED)

            filter_message = 'retrieving packets'
            if start_date is not None and end_date is None:
                filter_message += f' sent after {start_date:%Y-%m-%d %H:%M:%S}'
            elif start_date is None and end_date is not None:
                filter_message += f' sent before {end_date:%Y-%m-%d %H:%M:%S}'
            elif start_date is not None and end_date is not None:
                filter_message += f' sent between {start_date:%Y-%m-%d %H:%M:%S} and {end_date:%Y-%m-%d %H:%M:%S}'
            if callsigns is not None:
                filter_message += f' from {len(callsigns)} callsigns: {callsigns}'
            LOGGER.info(filter_message)

            connection_errors = []
            try:
                tncs = self.tncs
                self.__elements['tnc'].configure(state=tkinter.DISABLED)
                for tnc in tncs:
                    try:
                        if Path(tnc).suffix in ['.txt', '.log']:
                            tnc = RawAPRSTextFile(tnc, self.callsigns)
                            LOGGER.info(f'reading file {tnc.location}')
                        else:
                            tnc = SerialTNC(tnc, self.callsigns)
                            LOGGER.info(f'opened port {tnc.location}')
                        self.__connections.append(tnc)
                    except Exception as error:
                        connection_errors.append(f'TNC - {error}')
                self.tncs = [
                    connection.location
                    for connection in self.__connections
                    if isinstance(connection, SerialTNC)
                       or isinstance(connection, RawAPRSTextFile)
                ]

                api_key = self.__configuration['aprs_fi']['aprs_fi_key']
                if api_key is None:
                    api_key = simpledialog.askstring(
                        'APRS.fi API Key',
                        'enter API key for https://aprs.fi',
                        parent=self.__windows['main'],
                        show='*',
                    )
                try:
                    aprs_api = APRSfi(self.callsigns, api_key=api_key)
                    LOGGER.info(f'established connection to {aprs_api.location}')
                    self.__connections.append(aprs_api)
                    self.__configuration['aprs_fi']['aprs_fi_key'] = api_key
                except Exception as error:
                    connection_errors.append(f'aprs.fi - {error}')

                if (
                    'database' in self.__configuration
                    and self.__configuration['database']['database_hostname'] is not None
                ):
                    try:
                        ssh_tunnel_kwargs = {}
                        if 'ssh_tunnel' in self.__configuration:
                            ssh_hostname = self.__configuration['ssh_tunnel']['ssh_hostname']
                            if ssh_hostname is not None:
                                ssh_tunnel_kwargs.update(self.__configuration['ssh_tunnel'])
                                if '@' in ssh_hostname:
                                    (
                                        ssh_tunnel_kwargs['ssh_username'],
                                        ssh_tunnel_kwargs['ssh_hostname'],
                                    ) = ssh_hostname.split('@', 1)
                                if (
                                    'ssh_username' not in ssh_tunnel_kwargs
                                    or ssh_tunnel_kwargs['ssh_username'] is None
                                ):
                                    ssh_username = simpledialog.askstring(
                                        'SSH Tunnel Username',
                                        f'enter username for SSH host "{ssh_tunnel_kwargs["ssh_hostname"]}"',
                                        parent=self.__windows['main'],
                                    )
                                    if ssh_username is None or len(ssh_username) == 0:
                                        raise ConnectionError('missing SSH username')
                                    ssh_tunnel_kwargs['ssh_username'] = ssh_username

                                if (
                                    'ssh_password' not in ssh_tunnel_kwargs
                                    or ssh_tunnel_kwargs['ssh_password'] is None
                                ):
                                    password = simpledialog.askstring(
                                        'SSH Tunnel Password',
                                        f'enter password for SSH user '
                                        f'"{ssh_tunnel_kwargs["ssh_username"]}"',
                                        parent=self.__windows['main'],
                                        show='*',
                                    )
                                    if password is None or len(password) == 0:
                                        raise ConnectionError('missing SSH password')
                                    ssh_tunnel_kwargs['ssh_password'] = password

                        database_kwargs = {
                            key.replace('database_', ''): value
                            for key, value in self.__configuration['database'].items()
                        }
                        if (
                            'username' not in database_kwargs
                            or database_kwargs['username'] is None
                        ):
                            database_username = simpledialog.askstring(
                                'Database Username',
                                f'enter username for database '
                                f'"{database_kwargs["database_hostname"]}/'
                                f'{database_kwargs["database_database"]}"',
                                parent=self.__windows['main'],
                            )
                            if database_username is None or len(database_username) == 0:
                                raise ConnectionError('missing database username')
                            database_kwargs['username'] = database_username

                        if (
                            'password' not in database_kwargs
                            or database_kwargs['password'] is None
                        ):
                            database_password = simpledialog.askstring(
                                'Database Password',
                                f'enter password for database user '
                                f'"{database_kwargs["database_username"]}"',
                                parent=self.__windows['main'],
                                show='*',
                            )
                            if database_password is None or len(database_password) == 0:
                                raise ConnectionError('missing database password')
                            database_kwargs['password'] = database_password
                        if 'table' not in database_kwargs or database_kwargs['table'] is None:
                            database_table = simpledialog.askstring(
                                'Database Table',
                                f'enter database table name',
                                parent=self.__windows['main'],
                            )
                            if database_table is None or len(database_table) == 0:
                                raise ConnectionError('missing database table name')
                            database_kwargs['table'] = database_table

                        self.database = APRSDatabaseTable(
                            **database_kwargs, **ssh_tunnel_kwargs, callsigns=self.callsigns
                        )
                        LOGGER.info(f'connected to {self.database.location}')
                        self.__connections.append(self.database)
                        self.__configuration['database'].update(database_kwargs)
                        self.__configuration['ssh_tunnel'].update(ssh_tunnel_kwargs)
                    except ConnectionError as error:
                        connection_errors.append(f'database - {error}')
                        self.database = None
                else:
                    self.database = None

                if self.igate:
                    try:
                        self.aprs_is = APRSis(self.callsigns)
                    except ConnectionError as error:
                        connection_errors.append(f'igate - {error}')
                        self.aprs_is = None

                if len(self.__connections) == 0:
                    if self.output_filename is not None and self.output_filename.exists():
                        self.__connections.append(PacketGeoJSON(self.output_filename))
                    else:
                        connection_errors = '\n'.join(connection_errors)
                        raise ConnectionError(f'no connections started\n{connection_errors}')

                LOGGER.info(
                    f'listening for packets every {self.interval_seconds}s from {len(self.__connections)} '
                    f'connection(s): {", ".join([connection.location for connection in self.__connections])}'
                )

                for variable, enabled in self.__plot_toggles.items():
                    enabled = enabled.get()
                    if enabled and variable not in self.__plots:
                        self.__plots[variable] = LivePlot(
                            self.packet_tracks, variable, self.predictions
                        )
                    elif not enabled and variable in self.__plots:
                        self.__plots[variable].close()
                        del self.__plots[variable]

                set_child_states(self.__frames['configuration'], tkinter.DISABLED)

                for callsign in self.packet_tracks:
                    set_child_states(self.__windows[callsign], tkinter.DISABLED)

                self.__toggle_text.set('Stop')
                self.__running = True
            except Exception as error:
                messagebox.showerror(error.__class__.__name__, error)
                if '\n' in str(error):
                    for connection_error in str(error).split('\n'):
                        LOGGER.error(connection_error)
                else:
                    LOGGER.error(error)
                self.__running = False
                set_child_states(self.__frames['configuration'], tkinter.NORMAL)

            self.retrieve_packets()
        else:
            for connection in self.__connections:
                connection.close()

                if type(connection) is SerialTNC:
                    LOGGER.info(f'closing port {connection.location}')

            LOGGER.info(f'closed {len(self.__connections)} connections')

            for callsign in self.packet_tracks:
                set_child_states(self.__windows[callsign], tkinter.DISABLED)
            set_child_states(self.__frames['configuration'], tkinter.NORMAL)

            if not self.toggles['log_file']:
                set_child_states(self.__elements['log_file_box'], tkinter.DISABLED)
            if not self.toggles['output_file']:
                set_child_states(self.__elements['output_file_box'], tkinter.DISABLED)
            if not self.toggles['prediction_file']:
                set_child_states(self.__elements['prediction_file_box'], tkinter.DISABLED)

            self.__toggle_text.set('Start')
            self.__running = False
            self.__connections = []

            logging.shutdown()

    def retrieve_packets(self):
        if self.running:
            try:
                current_time = datetime.now()

                existing_callsigns = list(self.packet_tracks)

                new_packets = retrieve_packets(
                    self.__connections,
                    self.__packet_tracks,
                    self.database,
                    self.output_filename,
                    self.start_date,
                    self.end_date,
                    logger=LOGGER,
                )

                if self.toggles['prediction_file'] and len(new_packets) > 0:
                    try:
                        self.__predictions = get_predictions(
                            self.packet_tracks,
                            **{
                                key.replace('prediction_', ''): value
                                for key, value in self.__configuration['prediction'].items()
                                if 'prediction_' in key
                            },
                        )
                        if self.prediction_filename is not None:
                            write_packet_tracks(
                                self.__predictions.values(), self.prediction_filename
                            )
                    except PredictionError as error:
                        LOGGER.warning(f'{error.__class__.__name__} - {error}')
                    except Exception as error:
                        LOGGER.warning(
                            f'error retrieving prediction trajectory - {error.__class__.__name__} - {error}'
                        )

                if len(new_packets) > 0:
                    for variable, plot in self.__plots.items():
                        plot.update(self.packet_tracks, self.predictions)

                if self.aprs_is is not None:
                    for packets in new_packets.values():
                        self.aprs_is.send(packets)

                updated_callsigns = {
                    packet.from_callsign
                    for packets in new_packets.values()
                    for packet in packets
                    if isinstance(packet, APRSPacket)
                }
                for callsign in updated_callsigns:
                    packet_track = self.packet_tracks[callsign]
                    packet_time = datetime.utcfromtimestamp(
                        (packet_track.times[-1] - numpy.datetime64('1970-01-01T00:00:00Z'))
                        / numpy.timedelta64(1, 's')
                    )

                    if callsign not in existing_callsigns:
                        window = tkinter.Toplevel()
                        window.title(callsign)

                        self.__add_text_box(
                            window,
                            title=f'{callsign}.source',
                            label=None,
                            width=27,
                            sticky='w',
                            columnspan=3,
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.callsign',
                            label='Callsign',
                            width=17,
                            sticky='w',
                            columnspan=3,
                        )
                        self.replace_text(self.__elements[f'{callsign}.callsign'], callsign)
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.packets',
                            label='Packet #',
                            width=17,
                            sticky='w',
                            columnspan=3,
                        )

                        self.__add_text_box(
                            window,
                            title=f'{callsign}.time',
                            label='Time',
                            width=19,
                            sticky='w',
                            row=self.__elements[f'{callsign}.source'].grid_info()['row'],
                            column=self.__elements[f'{callsign}.source'].grid_info()['column']
                                   + 4,
                            columnspan=3,
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.age',
                            label='Packet Age',
                            width=14,
                            units='s',
                            sticky='w',
                            row=self.__elements[f'{callsign}.callsign'].grid_info()['row'],
                            column=self.__elements[f'{callsign}.callsign'].grid_info()[
                                       'column'
                                   ]
                                   + 3,
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.interval',
                            label='Interval',
                            width=14,
                            units='s',
                            sticky='w',
                            row=self.__elements[f'{callsign}.packets'].grid_info()['row'],
                            column=self.__elements[f'{callsign}.packets'].grid_info()['column']
                                   + 3,
                        )

                        separator = Separator(window, orient=tkinter.HORIZONTAL)
                        separator.grid(
                            row=window.grid_size()[1],
                            column=0,
                            columnspan=7,
                            sticky='ew',
                            pady=10,
                        )

                        self.__add_text_box(
                            window,
                            title=f'{callsign}.coordinates',
                            label='Lat., Lon.',
                            width=17,
                            sticky='w',
                            columnspan=3,
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.distance',
                            label='Distance',
                            width=14,
                            units='m',
                            sticky='w',
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.ground_speed',
                            label='Ground Speed',
                            width=14,
                            units='m/s',
                            sticky='w',
                        )

                        self.__add_text_box(
                            window,
                            title=f'{callsign}.altitude',
                            label='Alt.',
                            width=14,
                            units='m',
                            sticky='w',
                            row=self.__elements[f'{callsign}.coordinates'].grid_info()['row'],
                            column=self.__elements[f'{callsign}.coordinates'].grid_info()[
                                       'column'
                                   ]
                                   + 3,
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.ascent',
                            label='Ascent',
                            width=14,
                            units='m',
                            sticky='w',
                            row=self.__elements[f'{callsign}.distance'].grid_info()['row'],
                            column=self.__elements[f'{callsign}.distance'].grid_info()[
                                       'column'
                                   ]
                                   + 3,
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.ascent_rate',
                            label='Ascent Rate',
                            width=14,
                            units='m/s',
                            sticky='w',
                            row=self.__elements[f'{callsign}.ground_speed'].grid_info()['row'],
                            column=self.__elements[f'{callsign}.ground_speed'].grid_info()[
                                       'column'
                                   ]
                                   + 3,
                        )

                        separator = Separator(window, orient=tkinter.HORIZONTAL)
                        separator.grid(
                            row=window.grid_size()[1],
                            column=0,
                            columnspan=7,
                            sticky='ew',
                            pady=10,
                        )

                        self.__add_text_box(
                            window,
                            title=f'{callsign}.distance_downrange',
                            label='Downrange',
                            width=14,
                            units='m',
                            sticky='w',
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.distance_overground',
                            label='Overground',
                            width=14,
                            units='m',
                            sticky='w',
                        )

                        self.__add_text_box(
                            window,
                            title=f'{callsign}.maximum_altitude',
                            label='Max Alt.',
                            width=14,
                            units='m',
                            sticky='w',
                            row=self.__elements[f'{callsign}.distance_downrange'].grid_info()[
                                'row'
                            ],
                            column=self.__elements[
                                       f'{callsign}.distance_downrange'
                                   ].grid_info()['column']
                                   + 3,
                        )
                        self.__add_text_box(
                            window,
                            title=f'{callsign}.time_to_ground',
                            label='Est. Landing',
                            width=14,
                            units='s',
                            sticky='w',
                            row=self.__elements[f'{callsign}.distance_overground'].grid_info()[
                                'row'
                            ],
                            column=self.__elements[
                                       f'{callsign}.distance_overground'
                                   ].grid_info()['column']
                                   + 3,
                        )

                        separator = Separator(window, orient=tkinter.VERTICAL)
                        separator.grid(
                            row=0,
                            column=3,
                            rowspan=window.grid_size()[1] + 2,
                            sticky='ns',
                            padx=10,
                        )

                        window.protocol('WM_DELETE_WINDOW', window.iconify)

                        self.__windows[callsign] = window

                    window = self.__windows[callsign]

                    if window.state() == 'iconic':
                        window.deiconify()
                    if window.focus_get() is None:
                        window.focus_force()

                    set_child_states(window, tkinter.NORMAL)

                    self.replace_text(
                        self.__elements[f'{callsign}.packets'], len(packet_track)
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.source'], packet_track[-1].source
                    )
                    self.replace_text(self.__elements[f'{callsign}.time'], f'{packet_time}')
                    self.replace_text(
                        self.__elements[f'{callsign}.altitude'],
                        f'{packet_track.coordinates[-1, 2]:.3f}',
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.coordinates'],
                        ', '.join(
                            f'{value:.3f}'
                            for value in reversed(packet_track.coordinates[-1, :2])
                        ),
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.ascent'],
                        f'{packet_track.ascents[-1]:.2f}',
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.distance'],
                        f'{packet_track.overground_distances[-1]:.2f}',
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.interval'],
                        f'{packet_track.intervals[-1]:.2f}',
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.ascent_rate'],
                        f'{packet_track.ascent_rates[-1]:.2f}',
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.ground_speed'],
                        f'{packet_track.ground_speeds[-1]:.2f}',
                    )

                    self.replace_text(
                        self.__elements[f'{callsign}.distance_downrange'],
                        f'{packet_track.distance_downrange:.2f}',
                    )
                    self.replace_text(
                        self.__elements[f'{callsign}.distance_overground'],
                        f'{packet_track.length:.2f}',
                    )

                    self.replace_text(
                        self.__elements[f'{callsign}.maximum_altitude'],
                        f'{packet_track.coordinates[:, 2].max():.2f}',
                    )

                for callsign, packet_track in self.__packet_tracks.items():
                    window = self.__windows[callsign]
                    packet_time = datetime.utcfromtimestamp(
                        (packet_track.times[-1] - numpy.datetime64('1970-01-01T00:00:00Z'))
                        / numpy.timedelta64(1, 's')
                    )

                    time_to_ground_box = self.__elements[f'{callsign}.time_to_ground']
                    if packet_track.time_to_ground >= timedelta(seconds=0):
                        time_to_ground_box.configure(state=tkinter.NORMAL)
                        current_time_to_ground = (
                            packet_time + packet_track.time_to_ground - current_time
                        )
                        self.replace_text(
                            time_to_ground_box,
                            f'{current_time_to_ground / timedelta(seconds=1):.2f}',
                        )
                    else:
                        self.replace_text(time_to_ground_box, '')
                        time_to_ground_box.configure(state=tkinter.DISABLED)

                    set_child_states(window, tkinter.DISABLED, [tkinter.Text])

                    packet_age_box = self.__elements[f'{callsign}.age']
                    packet_age_box.configure(state=tkinter.NORMAL)
                    self.replace_text(
                        packet_age_box,
                        f'{(current_time - packet_time) / timedelta(seconds=1):.2f}',
                    )
                    packet_age_box.configure(state=tkinter.DISABLED)

                if self.running:
                    self.__windows['main'].after(
                        int(self.interval_seconds * 1000), self.retrieve_packets
                    )
            except KeyboardInterrupt:
                self.close()
            except Exception as error:
                LOGGER.exception(f'{error.__class__.__name__} - {error}')

    @staticmethod
    def replace_text(element: tkinter.Entry, value: str):
        if isinstance(element, tkinter.Text):
            start_index = '1.0'
        else:
            start_index = 0

        if value is None:
            value = ''

        element.delete(start_index, tkinter.END)
        element.insert(start_index, value)

    def close(self):
        try:
            if self.running:
                self.toggle()
            for plot in self.__plots.values():
                plot.close()
            self.__windows['main'].destroy()
        except Exception as error:
            LOGGER.exception(f'{error.__class__.__name__} - {error}')
        sys.exit()


def set_child_states(frame: tkinter.Frame, state: str = None, types: [type] = None):
    if state is None:
        state = tkinter.NORMAL
    for child in frame.winfo_children():
        if isinstance(child, tkinter.Frame):
            set_child_states(child, state, types)
        else:
            if types is None or any(
                isinstance(child, selected_type) for selected_type in types
            ):
                try:
                    child.configure(state=state)
                except tkinter.TclError:
                    continue
