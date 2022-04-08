import asyncio
from datetime import datetime, timedelta
import logging
from os import PathLike
from pathlib import Path
import re
import sys
from typing import Callable, Collection, Dict, List

from dateutil.parser import parse
import numpy
import teek
from teek.extras import more_dialogs

from packetraven import APRSfi, RawAPRSTextFile, SerialTNC
from packetraven.__main__ import packet_track_predictions, retrieve_packets
from packetraven.configuration.credentials import APRSfiCredentials
from packetraven.configuration.prediction import PredictionConfiguration
from packetraven.configuration.run import RunConfiguration
from packetraven.configuration.text import TextStreamConfiguration
from packetraven.connections.base import available_serial_ports, next_open_serial_port
from packetraven.connections.file import PacketGeoJSON
from packetraven.gui.plotting import LiveTrackPlot
from packetraven.packets import APRSPacket, LocationPacket
from packetraven.packets.tracks import LocationPacketTrack, PredictedTrajectory
from packetraven.packets.writer import write_packet_tracks
from packetraven.predicts import PredictionError


class PacketRavenGUI:
    def __init__(self, configuration: RunConfiguration = None):
        if configuration is None:
            configuration = RunConfiguration()

        main_window = teek.Window('PacketRaven')
        self.__windows = {'main': main_window}

        self.__configuration = configuration

        self.database = None
        self.aprs_is = None
        self.__connections = []

        self.__timeout = None
        self.__time_without_packets = timedelta(seconds=0)
        self.__running = False
        self.__toggles = {}
        self.__toggle_time = datetime.now()
        self.__packet_tracks = {}

        self.__frames = {}
        self.__elements = {}

        self.__plots = {}

        configuration_frame = teek.Frame(main_window)
        configuration_frame.grid(row=len(main_window.grid_rows), column=0, pady=10)
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

        separator = teek.Separator(configuration_frame, orient='horizontal')
        separator.grid(
            row=len(configuration_frame.grid_rows),
            column=0,
            columnspan=len(configuration_frame.grid_columns) + 1,
            sticky='ew',
            pady=10,
        )

        self.__add_entry_box(
            configuration_frame,
            title='callsigns',
            label='Callsigns',
            width=63,
            columnspan=len(configuration_frame.grid_columns),
        )
        self.__file_selection_option = 'select file(s)...'
        self.__add_combo_box(
            configuration_frame,
            title='text',
            label='Text',
            options=list(available_serial_ports()) + [self.__file_selection_option],
            option_select=self.__select_text_stream,
            width=60,
            columnspan=len(configuration_frame.grid_columns),
            sticky='w',
        )

        separator = teek.Separator(configuration_frame, orient='horizontal')
        separator.grid(
            row=len(configuration_frame.grid_rows),
            column=0,
            columnspan=len(configuration_frame.grid_columns) + 1,
            sticky='ew',
            pady=10,
        )

        log_file_label = teek.Label(configuration_frame, text='Log')
        log_file_label.grid(row=len(configuration_frame.grid_rows), column=0, sticky='w')

        log_file_frame = teek.Frame(configuration_frame)
        log_file_frame.grid(
            row=log_file_label.grid_info()['row'],
            column=1,
            columnspan=len(configuration_frame.grid_columns) - 1,
        )

        self.__toggles['log_to_file'] = teek.BooleanVar()
        self.__toggles['log_to_file'].set(self.__configuration['log']['filename'] is not None)
        log_file_checkbox = teek.Checkbutton(
            log_file_frame,
            variable=self.__toggles['log_to_file'],
            command=self.__toggle_log_file,
        )
        log_file_checkbox.grid(row=0, column=0, padx=10)

        self.__elements['log_file_box'] = self.__add_file_box(
            log_file_frame,
            row=0,
            column=1,
            title='log_file',
            file_select=self.__select_log_file,
            width=52,
            sticky='w',
        )

        output_file_label = teek.Label(configuration_frame, text='Output')
        output_file_label.grid(row=len(configuration_frame.grid_rows), column=0, sticky='w')

        output_file_frame = teek.Frame(configuration_frame)
        output_file_frame.grid(
            row=output_file_label.grid_info()['row'],
            column=1,
            columnspan=len(configuration_frame.grid_columns) - 1,
        )

        self.__toggles['output_to_file'] = teek.BooleanVar()
        self.__toggles['output_to_file'].set(
            self.__configuration['output']['filename'] is not None
        )
        output_file_checkbox = teek.Checkbutton(
            output_file_frame,
            variable=self.__toggles['output_to_file'],
            command=self.__toggle_output_file,
        )
        output_file_checkbox.grid(row=0, column=0, padx=10)

        self.__elements['output_file_box'] = self.__add_file_box(
            output_file_frame,
            row=0,
            column=1,
            title='output_file',
            file_select=self.__select_output_file,
            width=52,
            sticky='w',
        )

        separator = teek.Separator(configuration_frame, orient='horizontal')
        separator.grid(
            row=len(configuration_frame.grid_rows),
            column=0,
            columnspan=len(configuration_frame.grid_columns) + 1,
            sticky='ew',
            pady=10,
        )

        prediction_label = teek.Label(configuration_frame, text='Predict')
        prediction_label.grid(row=len(configuration_frame.grid_rows), column=0, sticky='w')

        prediction_frame = teek.Frame(configuration_frame)
        prediction_frame.grid(
            row=prediction_label.grid_info()['row'],
            column=1,
            columnspan=len(configuration_frame.grid_columns) - 1,
        )

        self.__toggles['run_prediction'] = teek.BooleanVar()
        self.__toggles['run_prediction'].set(self.__configuration['prediction'] is not None)
        prediction_checkbox = teek.Checkbutton(
            prediction_frame,
            variable=self.__toggles['run_prediction'],
            command=self.__toggle_prediction_file,
        )
        prediction_checkbox.grid(row=0, column=0, padx=10)

        self.__elements['prediction_file_box'] = self.__add_file_box(
            prediction_frame,
            row=0,
            column=1,
            title='prediction_file',
            file_select=self.__select_prediction_file,
            width=52,
            sticky='w',
        )

        separator = teek.Separator(configuration_frame, orient='horizontal')
        separator.grid(
            row=len(configuration_frame.grid_rows),
            column=0,
            columnspan=len(configuration_frame.grid_columns) + 1,
            sticky='ew',
            pady=10,
        )

        plot_label = teek.Label(configuration_frame, text='Plots')
        plot_label.grid(row=len(configuration_frame.grid_rows), column=0, sticky='w')

        plot_checkbox_frame = teek.Frame(configuration_frame)
        plot_checkbox_frame.grid(
            row=plot_label.grid_info()['row'],
            column=0,
            columnspan=len(configuration_frame.grid_columns) - 1,
        )

        plot_variables = ['altitude', 'ascent_rate', 'ground_speed']
        self.__plot_toggles = {}
        for plot_index, plot in enumerate(plot_variables):
            boolean_var = teek.BooleanVar()
            boolean_var.set(self.__configuration['plots'][plot])
            plot_checkbox = teek.Checkbutton(
                plot_checkbox_frame, text=plot, variable=boolean_var
            )
            plot_checkbox.grid(row=0, column=plot_index, padx=10)
            self.__plot_toggles[plot] = boolean_var

        separator = teek.Separator(main_window, orient='horizontal')
        separator.grid(row=len(main_window.grid_rows), column=0, sticky='ew')

        control_frame = teek.Frame(main_window)
        control_frame.grid(row=len(main_window.grid_rows), column=0, pady=10)
        self.__frames['controls'] = control_frame

        self.__toggle_text = teek.StringVar()
        self.__toggle_text.set('Start')
        toggle_button = teek.Button(
            control_frame, textvariable=self.__toggle_text, command=self.toggle
        )
        toggle_button.grid(row=len(control_frame.grid_rows), column=0, sticky='nsew')
        self.__elements['toggle_button'] = toggle_button

        self.callsigns = self.__configuration['callsigns']

        if (
            'text' in self.__configuration['packets']
            and self.__configuration['packets']['text'] is not None
        ):
            self.text_streams = self.__configuration['packets']['text']['locations']

        start_date = self.__configuration['time']['start']
        if start_date is not None:
            self.start_date = start_date
        end_date = self.__configuration['time']['end']
        if end_date is not None:
            self.end_date = end_date

        self.log_filename = self.__configuration['log']['filename']
        if self.log_filename is None:
            self.log_filename = Path('~') / 'Desktop'
        self.__toggle_log_file()

        self.output_filename = self.__configuration['output']['filename']
        if self.output_filename is None:
            self.output_filename = Path('~') / 'Desktop'
        self.__toggle_output_file()

        if (
            'prediction' in self.__configuration
            and self.__configuration['prediction'] is not None
        ):
            self.prediction_filename = self.__configuration['prediction']['output']['filename']
        if self.prediction_filename is None:
            self.prediction_filename = Path('~') / 'Desktop'
        self.__toggle_prediction_file()
        self.__predictions = {}

        self.__windows['main'].on_delete_window.connect(self.close)

        teek.run()

    @property
    def callsigns(self) -> List[str]:
        return self.__configuration['callsigns']

    @property
    def interval(self) -> timedelta:
        return self.__configuration['time']['interval']

    @property
    def callsigns(self) -> List[str]:
        callsigns = self.__elements['callsigns'].text
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
    def callsigns(self, callsigns: List[str]):
        if callsigns is not None:
            callsigns = ', '.join([callsign.upper() for callsign in callsigns])
        else:
            callsigns = ''
        self.__replace_text(self.__elements['callsigns'], callsigns)

    @property
    def text_streams(self) -> List[str]:
        """ locations of text streams (for instance a TNC parsing APRS audio into ASCII frames over USB) """
        streams = []
        for stream in self.__elements['text'].text.split(','):
            stream = stream.strip()
            if len(stream) > 0:
                if stream.upper() == 'AUTO':
                    try:
                        stream = next_open_serial_port()
                    except OSError:
                        logging.warning(f'no open serial ports')
                        stream = None
                streams.append(stream)
        return streams

    @text_streams.setter
    def text_streams(self, filenames: List[PathLike]):
        if filenames is None:
            filenames = []
        elif not isinstance(filenames, Collection) or isinstance(filenames, str):
            filenames = [filenames]

        filenames = [str(filename) for filename in filenames]

        if (
            'text' in self.__configuration['packets']
            and self.__configuration['packets']['text'] is not None
        ):
            self.__configuration['packets']['text']['locations'] = filenames
        else:
            self.__configuration['packets']['text'] = TextStreamConfiguration(
                location=filenames
            )
        self.__replace_text(self.__elements['text'], ', '.join(filenames))

    @property
    def start_date(self) -> datetime:
        start_date = self.__elements['start_date'].text
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
        self.__replace_text(self.__elements['start_date'], start_date)

    @property
    def end_date(self) -> datetime:
        end_date = self.__elements['end_date'].text
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
        self.__replace_text(self.__elements['end_date'], end_date)

    @property
    def log_filename(self) -> Path:
        if self.toggles['log_to_file']:
            filename = self.__elements['log_file'].text
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
                filename = (
                    filename
                    / f'{self.__configuration["name"]}_log_{self.__toggle_time:%Y%m%dT%H%M%S}.txt'
                )
        else:
            filename = ''
        self.__replace_text(self.__elements['log_file'], filename)

    @property
    def output_filename(self) -> Path:
        if self.toggles['output_to_file']:
            filename = self.__elements['output_file'].text
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
                    filename
                    / f'{self.__configuration["name"]}_{self.__toggle_time:%Y%m%dT%H%M%S}.geojson'
                )
        else:
            filename = ''
        self.__replace_text(self.__elements['output_file'], filename)

    @property
    def prediction_filename(self) -> Path:
        if self.toggles['run_prediction']:
            filename = self.__elements['prediction_file'].text
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
        if self.__configuration['prediction'] is None:
            self.__configuration['prediction'] = PredictionConfiguration(
                output={'filename': filename}
            )
        else:
            self.__configuration['prediction']['output']['filename'] = filename
        if filename is not None:
            if not isinstance(filename, Path):
                filename = Path(filename)
            if filename.expanduser().resolve().is_dir():
                filename = (
                    filename
                    / f'{self.__configuration["name"]}_predict_{self.__toggle_time:%Y%m%dT%H%M%S}.geojson'
                )
        else:
            filename = ''
        self.__replace_text(self.__elements['prediction_file'], filename)

    @property
    def toggles(self) -> Dict[str, bool]:
        return {key: value.get() for key, value in self.__toggles.items()}

    @property
    def running(self) -> bool:
        return self.__running

    @running.setter
    def running(self, running: bool):
        if running is not self.running:
            self.toggle()

    @property
    def packet_tracks(self) -> Dict[str, LocationPacketTrack]:
        return self.__packet_tracks

    @property
    def predictions(self) -> Dict[str, PredictedTrajectory]:
        return self.__predictions if self.toggles['run_prediction'] else None

    def toggle(self):
        if not self.running:
            self.__toggle_time = datetime.now()

            self.__elements['toggle_button'].busy_hold()
            self.__toggle_text.set('Stop')

            if self.log_filename is not None:
                logging.basicConfig(filename=self.log_filename)

            if self.toggles['log_to_file']:
                set_child_states(self.__elements['log_file_box'], 'disabled')

            start_date = self.start_date
            self.__elements['start_date'].config['state'] = 'disabled'

            end_date = self.end_date
            self.__elements['end_date'].config['state'] = 'disabled'

            callsigns = self.callsigns
            self.__elements['callsigns'].config['state'] = 'disabled'

            filter_message = 'retrieving packets'
            if start_date is not None and end_date is None:
                filter_message += f' sent after {start_date:%Y-%m-%d %H:%M:%S}'
            elif start_date is None and end_date is not None:
                filter_message += f' sent before {end_date:%Y-%m-%d %H:%M:%S}'
            elif start_date is not None and end_date is not None:
                filter_message += f' sent between {start_date:%Y-%m-%d %H:%M:%S} and {end_date:%Y-%m-%d %H:%M:%S}'
            if callsigns is not None:
                filter_message += f' from {len(callsigns)} callsigns: {callsigns}'
            logging.info(filter_message)

            connection_errors = []
            try:
                streams = self.text_streams
                self.__elements['text'].config['state'] = 'disabled'
                for stream in streams:
                    try:
                        if Path(stream).suffix in ['.txt', '.log']:
                            stream = RawAPRSTextFile(stream, self.callsigns)
                            logging.info(f'reading file {stream.location}')
                        else:
                            stream = SerialTNC(stream, self.callsigns)
                            logging.info(f'opened port {stream.location}')
                        self.__connections.append(stream)
                    except Exception as error:
                        connection_errors.append(f'text stream - {error}')
                self.text_streams = [
                    connection.location
                    for connection in self.__connections
                    if isinstance(connection, SerialTNC)
                    or isinstance(connection, RawAPRSTextFile)
                ]

                if (
                    'aprs_fi' in self.__configuration['packets']
                    and self.__configuration['packets']['aprs_fi'] is not None
                ):
                    api_key = self.__configuration['packets']['aprs_fi']['api_key']
                else:
                    api_key = None
                if api_key is None:
                    api_key = more_dialogs.ask_string(
                        'APRS.fi API Key',
                        'enter API key for https://aprs.fi \n'
                        'leave blank (or Cancel) for none',
                        parent=self.__windows['main'],
                    )
                try:
                    aprs_api = APRSfi(self.callsigns, api_key=api_key)
                    logging.info(f'established connection to {aprs_api.location}')
                    self.__connections.append(aprs_api)
                    if self.__configuration['packets']['aprs_fi'] is None:
                        self.__configuration['packets']['aprs_fi'] = APRSfiCredentials(
                            api_key=api_key
                        )
                    else:
                        self.__configuration['packets']['aprs_fi']['api_key'] = api_key
                except Exception as error:
                    connection_errors.append(f'aprs.fi - {error}')

                if (
                    'database' in self.__configuration['packets']
                    and self.__configuration['packets']['database'] is not None
                ):
                    try:
                        ssh_tunnel_credentials = self.__configuration['packets']['database'][
                            'tunnel'
                        ]
                        if ssh_tunnel_credentials is not None:
                            ssh_hostname = ssh_tunnel_credentials['hostname']
                            if '@' in ssh_hostname:
                                (
                                    ssh_tunnel_credentials['username'],
                                    ssh_tunnel_credentials['hostname'],
                                ) = ssh_hostname.split('@', 1)
                            if ssh_tunnel_credentials['username'] is None:
                                ssh_username = more_dialogs.ask_string(
                                    'SSH Tunnel Username',
                                    f'enter username for SSH host "{ssh_tunnel_credentials["hostname"]}"',
                                    parent=self.__windows['main'],
                                )
                                if ssh_username is None or len(ssh_username) == 0:
                                    raise ConnectionError('missing SSH username')
                                ssh_tunnel_credentials['username'] = ssh_username

                            if ssh_tunnel_credentials['password'] is None:
                                password = more_dialogs.ask_string(
                                    'SSH Tunnel Password',
                                    f'enter password for SSH user '
                                    f'"{ssh_tunnel_credentials["username"]}"',
                                    parent=self.__windows['main'],
                                )
                                if password is None or len(password) == 0:
                                    raise ConnectionError('missing SSH password')
                                ssh_tunnel_credentials['password'] = password

                        database_credentials = self.__configuration['packets']['database']
                        if database_credentials['username'] is None:
                            database_username = more_dialogs.ask_string(
                                'Database Username',
                                f'enter username for database '
                                f'"{database_credentials["database_hostname"]}/'
                                f'{database_credentials["database_database"]}"',
                                parent=self.__windows['main'],
                            )
                            if database_username is None or len(database_username) == 0:
                                raise ConnectionError('missing database username')
                            database_credentials['username'] = database_username

                        if database_credentials['password'] is None:
                            database_password = more_dialogs.ask_string(
                                'Database Password',
                                f'enter password for database user '
                                f'"{database_credentials["database_username"]}"',
                                parent=self.__windows['main'],
                            )
                            if database_password is None or len(database_password) == 0:
                                raise ConnectionError('missing database password')
                            database_credentials['password'] = database_password
                        if database_credentials['table'] is None:
                            database_table = more_dialogs.ask_string(
                                'Database Table',
                                f'enter database table name',
                                parent=self.__windows['main'],
                            )
                            if database_table is None or len(database_table) == 0:
                                raise ConnectionError('missing database table name')
                            database_credentials['table'] = database_table

                        self.database = database_credentials.packet_source(callsigns=callsigns)
                        logging.info(f'connected to {self.database.location}')
                        self.__connections.append(self.database)
                    except ConnectionError as error:
                        connection_errors.append(f'database - {error}')
                        self.database = None
                else:
                    self.database = None

                if (
                    'aprs_is' in self.__configuration['packets']
                    and self.__configuration['packets']['aprs_is'] is not None
                ):
                    try:
                        self.aprs_is = self.__configuration['packets'][
                            'aprs_is'
                        ].packet_source(callsigns=self.callsigns)
                    except ConnectionError as error:
                        connection_errors.append(f'igate - {error}')
                        self.aprs_is = None

                if len(self.__connections) == 0:
                    if self.output_filename is not None and self.output_filename.exists():
                        self.__connections.append(PacketGeoJSON(self.output_filename))
                    else:
                        connection_errors = '\n'.join(connection_errors)
                        raise ConnectionError(f'no connections started\n{connection_errors}')

                logging.info(
                    f'listening for packets every {self.interval} from {len(self.__connections)} '
                    f'connection(s): {", ".join([connection.location for connection in self.__connections])}'
                )

                for variable, enabled in self.__plot_toggles.items():
                    enabled = enabled.get()
                    if enabled and variable not in self.__plots:
                        self.__plots[variable] = LiveTrackPlot(
                            self.packet_tracks, variable, self.predictions
                        )
                    elif not enabled and variable in self.__plots:
                        self.__plots[variable].close()
                        del self.__plots[variable]

                set_child_states(self.__frames['configuration'], 'disabled')

                for callsign in self.packet_tracks:
                    set_child_states(self.__windows[callsign], 'disabled')

                self.__running = True
            except Exception as error:
                error_message = f'{error.__class__.__name__} - {error}'
                if '\n' in error_message:
                    for error_line in error_message.split('\n'):
                        logging.error(error_line)
                else:
                    logging.exception(error)
                _, error, error_traceback = sys.exc_info()
                filename = error_traceback.tb_frame.f_code.co_filename
                line_number = error_traceback.tb_lineno
                teek.dialog.error(
                    error.__class__.__name__, f'{error_message}\n\n{filename}:{line_number}'
                )
                self.__running = False
                set_child_states(self.__frames['configuration'], 'normal')

            self.__elements['toggle_button'].busy_forget()
            asyncio.run(self.retrieve_packets())
        else:
            if self.__timeout is not None:
                try:
                    self.__timeout.cancel()
                except RuntimeError:
                    pass

            for connection in self.__connections:
                connection.close()

                if type(connection) is SerialTNC:
                    logging.info(f'closing port {connection.location}')

            logging.info(f'closed {len(self.__connections)} connections')

            for callsign in self.packet_tracks:
                set_child_states(self.__windows[callsign], 'disabled')
            set_child_states(self.__frames['configuration'], 'normal')

            if not self.toggles['log_to_file']:
                set_child_states(self.__elements['log_file_box'], 'disabled')
            if not self.toggles['output_to_file']:
                set_child_states(self.__elements['output_file_box'], 'disabled')
            if not self.toggles['run_prediction']:
                set_child_states(self.__elements['prediction_file_box'], 'disabled')

            self.__toggle_text.set('Start')
            self.__running = False
            self.__connections = []

            logging.shutdown()

    async def retrieve_packets(self):
        if self.running:
            try:
                current_time = datetime.now()

                new_packets = retrieve_packets(
                    self.__connections,
                    self.__packet_tracks,
                    self.database,
                    self.start_date,
                    self.end_date,
                )

                output_filename_index = None
                for index, connection in enumerate(self.__connections):
                    if isinstance(connection, PacketGeoJSON):
                        output_filename_index = index
                if output_filename_index is not None:
                    self.__connections.pop(output_filename_index)

                if self.toggles['run_prediction']:
                    try:
                        self.__predictions.update(
                            packet_track_predictions(
                                self.packet_tracks, self.__configuration['prediction'],
                            )
                        )
                        if self.prediction_filename is not None:
                            write_packet_tracks(
                                self.__predictions.values(), self.prediction_filename
                            )
                    except PredictionError as error:
                        logging.warning(f'{error.__class__.__name__} - {error}')
                    except Exception as error:
                        logging.exception(
                            f'error retrieving prediction trajectory - {error.__class__.__name__} - {error}'
                        )

                if len(new_packets) > 0:
                    if self.output_filename is not None:
                        write_packet_tracks(
                            [
                                self.__packet_tracks[callsign]
                                for callsign in self.__packet_tracks
                            ],
                            self.output_filename,
                        )

                    await self.__update_sources_window(new_packets)

                    if self.aprs_is is not None:
                        for packets in new_packets.values():
                            self.aprs_is.send(packets)

                    for plot in self.__plots.values():
                        plot.update(self.packet_tracks, self.predictions)

                    updated_callsigns = {
                        packet.from_callsign
                        for packets in new_packets.values()
                        for packet in packets
                        if isinstance(packet, APRSPacket)
                    }
                else:
                    updated_callsigns = {}
                    self.__time_without_packets += self.interval + (
                        datetime.now() - current_time
                    )

                if len(self.__packet_tracks) > 0:
                    await asyncio.wait(
                        [
                            self.__update_callsign_window(
                                callsign,
                                only_time=callsign not in updated_callsigns,
                                current_time=current_time,
                            )
                            for callsign, packet_track in self.__packet_tracks.items()
                        ]
                    )

                if (
                    'timeout' in self.__configuration['time']
                    and self.__time_without_packets >= self.__configuration['time']['timeout']
                ):
                    message = f'shutting down - no packets received for {self.__time_without_packets}'
                    logging.info(message)
                    teek.dialog.info('timeout', message)
                    self.close()

                if self.running:
                    self.__timeout = teek.after(
                        ms=int(self.interval / timedelta(seconds=1)) * 1000,
                        callback=asyncio.run,
                        kwargs={'main': self.retrieve_packets()},
                    )
            except KeyboardInterrupt:
                self.close()
            except Exception as error:
                logging.exception(f'{error.__class__.__name__} - {error}')

    def close(self):
        try:
            if self.running:
                self.toggle()
            for plot in self.__plots.values():
                plot.close()
            teek.quit()
        except Exception as error:
            logging.exception(f'{error.__class__.__name__} - {error}')
        sys.exit()

    def __select_text_stream(self):
        if self.__elements['stream'].text == self.__file_selection_option:
            self.text_streams = teek.dialog.open_multiple_files(
                title='Select text file(s)...',
                defaultextension='.txt',
                filetypes=[('Text', '*.txt'), ('JSON', '*.json'), ('GeoJSON', '*.geojson')],
            )

    def __select_log_file(self):
        self.log_filename = teek.dialog.save_file(
            title='Create log file...',
            initialdir=str(self.log_filename.parent),
            initialfile=self.log_filename.stem,
            defaultextension='.txt',
            filetypes=[('Text', '*.txt')],
        )

    def __select_output_file(self):
        self.output_filename = teek.dialog.save_file(
            title='Create output file...',
            initialdir=str(self.output_filename.parent),
            initialfile=self.output_filename.stem,
            defaultextension='.geojson',
            filetypes=[
                ('GeoJSON', '*.geojson'),
                ('Text', '*.txt'),
                ('Keyhole Markup Language', '*.kml'),
            ],
        )

    def __select_prediction_file(self):
        self.prediction_filename = teek.dialog.save_file(
            title='Create predict file...',
            initialdir=str(self.prediction_filename.parent),
            initialfile=self.prediction_filename.stem,
            defaultextension='.geojson',
            filetypes=[
                ('GeoJSON', '*.geojson'),
                ('Text', '*.txt'),
                ('Keyhole Markup Language', '*.kml'),
            ],
        )

    def __toggle_log_file(self, value: bool = None):
        if (value is not None and value) or self.toggles['log_to_file']:
            set_child_states(self.__elements['log_file_box'], state='normal')
            logging.basicConfig(filename=self.log_filename)
        else:
            set_child_states(self.__elements['log_file_box'], state='disabled')
            logging.basicConfig(filename=None)

    def __toggle_output_file(self, value: bool = None):
        if (value is not None and value) or self.toggles['output_to_file']:
            set_child_states(self.__elements['output_file_box'], state='normal')
        else:
            set_child_states(self.__elements['output_file_box'], state='disabled')

    def __toggle_prediction_file(self, value: bool = None):
        if (value is not None and value) or self.toggles['run_prediction']:
            set_child_states(self.__elements['prediction_file_box'], state='normal')
        else:
            set_child_states(self.__elements['prediction_file_box'], state='disabled')

    def __add_callsign_window(self, callsign: str) -> teek.Window:
        window = teek.Window(callsign)

        self.__add_text_box(
            window, title=f'{callsign}.source', label=None, width=27, sticky='w', columnspan=3,
        )
        self.__add_text_box(
            window,
            title=f'{callsign}.callsign',
            label='Callsign',
            width=17,
            sticky='w',
            columnspan=3,
        )
        self.__replace_text(self.__elements[f'{callsign}.callsign'], callsign)
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
            column=self.__elements[f'{callsign}.source'].grid_info()['column'] + 4,
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
            column=self.__elements[f'{callsign}.callsign'].grid_info()['column'] + 3,
        )
        self.__add_text_box(
            window,
            title=f'{callsign}.interval',
            label='Interval',
            width=14,
            units='s',
            sticky='w',
            row=self.__elements[f'{callsign}.packets'].grid_info()['row'],
            column=self.__elements[f'{callsign}.packets'].grid_info()['column'] + 3,
        )

        separator = teek.Separator(window, orient='horizontal')
        separator.grid(
            row=len(window.grid_rows), column=0, columnspan=7, sticky='ew', pady=10,
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
            column=self.__elements[f'{callsign}.coordinates'].grid_info()['column'] + 3,
        )
        self.__add_text_box(
            window,
            title=f'{callsign}.ascent',
            label='Ascent',
            width=14,
            units='m',
            sticky='w',
            row=self.__elements[f'{callsign}.distance'].grid_info()['row'],
            column=self.__elements[f'{callsign}.distance'].grid_info()['column'] + 3,
        )
        self.__add_text_box(
            window,
            title=f'{callsign}.ascent_rate',
            label='Ascent Rate',
            width=14,
            units='m/s',
            sticky='w',
            row=self.__elements[f'{callsign}.ground_speed'].grid_info()['row'],
            column=self.__elements[f'{callsign}.ground_speed'].grid_info()['column'] + 3,
        )

        separator = teek.Separator(window, orient='horizontal')
        separator.grid(
            row=len(window.grid_rows), column=0, columnspan=7, sticky='ew', pady=10,
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
            row=self.__elements[f'{callsign}.distance_downrange'].grid_info()['row'],
            column=self.__elements[f'{callsign}.distance_downrange'].grid_info()['column'] + 3,
        )
        self.__add_text_box(
            window,
            title=f'{callsign}.time_to_ground',
            label='Est. Landing',
            width=14,
            units='s',
            sticky='w',
            row=self.__elements[f'{callsign}.distance_overground'].grid_info()['row'],
            column=self.__elements[f'{callsign}.distance_overground'].grid_info()['column']
            + 3,
        )

        separator = teek.Separator(window, orient='vertical')
        separator.grid(
            row=0, column=3, rowspan=len(window.grid_rows) + 2, sticky='ns', padx=10,
        )

        window.on_delete_window.connect(window.iconify)

        self.__windows[callsign] = window

        return window

    async def __update_callsign_window(
        self, callsign: str, only_time: bool = False, current_time: datetime = None
    ):
        if callsign not in self.__windows:
            self.__add_callsign_window(callsign)

        if current_time is None:
            current_time = datetime.now()

        window = self.__windows[callsign]

        if not only_time:
            window.deiconify()
            window.focus()

        set_child_states(window, 'normal')

        packet_track = self.packet_tracks[callsign]

        packet_time = datetime.utcfromtimestamp(
            (packet_track.times[-1] - numpy.datetime64('1970-01-01T00:00:00Z'))
            / numpy.timedelta64(1, 's')
        )

        if not only_time:
            self.__replace_text(self.__elements[f'{callsign}.packets'], len(packet_track))
            self.__replace_text(self.__elements[f'{callsign}.source'], packet_track[-1].source)
            self.__replace_text(self.__elements[f'{callsign}.time'], f'{packet_time}')
            self.__replace_text(
                self.__elements[f'{callsign}.altitude'],
                f'{packet_track.coordinates[-1, 2]:.3f}',
            )
            self.__replace_text(
                self.__elements[f'{callsign}.coordinates'],
                ', '.join(
                    f'{value:.3f}' for value in reversed(packet_track.coordinates[-1, :2])
                ),
            )
            self.__replace_text(
                self.__elements[f'{callsign}.ascent'], f'{packet_track.ascents[-1]:.2f}',
            )
            self.__replace_text(
                self.__elements[f'{callsign}.distance'],
                f'{packet_track.overground_distances[-1]:.2f}',
            )
            self.__replace_text(
                self.__elements[f'{callsign}.interval'],
                f'{packet_track.intervals[-1] / numpy.timedelta64(1, "s"):.2f}',
            )
            self.__replace_text(
                self.__elements[f'{callsign}.ascent_rate'],
                f'{packet_track.ascent_rates[-1]:.2f}',
            )
            self.__replace_text(
                self.__elements[f'{callsign}.ground_speed'],
                f'{packet_track.ground_speeds[-1]:.2f}',
            )

            self.__replace_text(
                self.__elements[f'{callsign}.distance_downrange'],
                f'{packet_track.distance_downrange:.2f}',
            )
            self.__replace_text(
                self.__elements[f'{callsign}.distance_overground'],
                f'{packet_track.length:.2f}',
            )

            self.__replace_text(
                self.__elements[f'{callsign}.maximum_altitude'],
                f'{packet_track.coordinates[:, 2].max():.2f}',
            )

        time_to_ground_box = self.__elements[f'{callsign}.time_to_ground']
        if packet_track.time_to_ground >= timedelta(seconds=0):
            time_to_ground_box.config['state'] = 'normal'
            current_time_to_ground = packet_time + packet_track.time_to_ground - current_time
            self.__replace_text(
                time_to_ground_box, f'{current_time_to_ground / timedelta(seconds=1):.2f}',
            )
        else:
            self.__replace_text(time_to_ground_box, '')
            time_to_ground_box.config['state'] = 'disabled'

        set_child_states(window, 'disabled', [teek.Text])

        packet_age_box = self.__elements[f'{callsign}.age']
        packet_age_box.config['state'] = 'normal'
        self.__replace_text(
            packet_age_box, f'{(current_time - packet_time) / timedelta(seconds=1):.2f}',
        )
        packet_age_box.config['state'] = 'disabled'

    def __add_sources_window(self) -> teek.Window:
        sources_window = teek.Window('sources')
        for index, connection in enumerate(self.__connections):
            self.__add_text_box(
                sources_window,
                title=f'sources.source_{index}_location',
                label=None,
                width=40,
                sticky='w',
            )
            self.__add_text_box(
                sources_window,
                title=f'sources.source_{index}_packets',
                label='packets',
                width=5,
                sticky='w',
                row=self.__elements[f'sources.source_{index}_location'].grid_info()['row'],
                column=self.__elements[f'sources.source_{index}_location'].grid_info()[
                    'column'
                ]
                + 1,
            )
            self.__replace_text(
                self.__elements[f'sources.source_{index}_location'], connection.location,
            )
        sources_window.on_delete_window.connect(sources_window.iconify)
        self.__windows['sources'] = sources_window

        for index, connection in enumerate(self.__connections):
            self.__replace_text(
                self.__elements[f'sources.source_{index}_packets'], 0,
            )

        return sources_window

    async def __update_sources_window(self, sources: Dict[str, List[LocationPacket]]):
        if 'sources' not in self.__windows:
            window = self.__add_sources_window()
        else:
            window = self.__windows['sources']

        for index, connection in enumerate(self.__connections):
            for source, packets in sources.items():
                if source == connection.location:
                    if f'sources.source_{index}_packets' not in self.__elements:
                        self.__add_text_box(
                            window,
                            title=f'sources.source_{index}_location',
                            label=None,
                            width=40,
                            sticky='w',
                        )
                        self.__add_text_box(
                            window,
                            title=f'sources.source_{index}_packets',
                            label='packets',
                            width=5,
                            sticky='w',
                            row=self.__elements[
                                f'sources.source_{index}_location'
                            ].grid_info()['row'],
                            column=self.__elements[
                                f'sources.source_{index}_location'
                            ].grid_info()['column']
                            + 1,
                        )
                        self.__replace_text(
                            self.__elements[f'sources.source_{index}_location'],
                            connection.location,
                        )
                        self.__replace_text(
                            self.__elements[f'sources.source_{index}_packets'], 0,
                        )
                    self.__replace_text(
                        self.__elements[f'sources.source_{index}_packets'],
                        int(self.__elements[f'sources.source_{index}_packets'].get())
                        + len(packets),
                    )

    def __add_combo_box(
        self,
        frame: teek.Frame,
        title: str,
        options: List[str],
        option_select: Callable = None,
        **kwargs,
    ) -> teek.Combobox:
        width = kwargs['width'] if 'width' in kwargs else None
        combo_box = teek.Combobox(frame, width=width)
        combo_box.config['values'] = options
        if option_select is not None:
            combo_box.bind('<<ComboboxSelected>>', option_select)
        return self.__add_text_box(frame, title, text_box=combo_box, **kwargs)

    def __add_file_box(
        self, frame: teek.Frame, title: str, file_select: Callable, **kwargs
    ) -> teek.Frame:
        if 'row' not in kwargs:
            kwargs['row'] = len(frame.grid_rows)
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
            text_label = teek.Label(frame, text=kwargs['label'])
            text_label.grid(row=kwargs['row'], column=kwargs['column'], sticky='w')
            file_box_kwargs['column'] += 1

        file_box_frame = teek.Frame(frame)
        file_box_frame.grid(**file_box_kwargs)

        file_box = teek.Entry(
            file_box_frame, width=kwargs['width'] if 'width' in kwargs else None
        )
        file_button = teek.Button(file_box_frame, text='...', command=file_select)

        file_box.pack(side='left')
        file_button.pack(side='left')

        self.__elements[title] = file_box
        return file_box_frame

    def __add_entry_box(self, frame: teek.Frame, title: str, **kwargs) -> teek.Entry:
        if 'text_box' not in kwargs:
            kwargs['text_box'] = teek.Entry(
                frame, width=kwargs['width'] if 'width' in kwargs else None
            )
        return self.__add_text_box(frame, title, **kwargs)

    def __add_text_box(
        self,
        frame: teek.Frame,
        title: str,
        label: str,
        units: str = None,
        row: int = None,
        column: int = None,
        width: int = 10,
        text_box: teek.Entry = None,
        **kwargs,
    ) -> teek.Text:
        if row is None:
            row = len(frame.grid_rows)
        if column is None:
            column = 0

        if 'columnspan' in kwargs:
            if label is not None:
                kwargs['columnspan'] -= 1
            if units is not None:
                kwargs['columnspan'] -= 1

        if label is not None:
            text_label = teek.Label(frame, text=label)
            text_label.grid(row=row, column=column, sticky='w')
            column += 1

        if text_box is None:
            text_box = teek.Text(frame, width=width, height=1)
        text_box.grid(row=row, column=column, **kwargs)
        column += 1

        if units is not None:
            units_label = teek.Label(frame, text=units)
            units_label.grid(row=row, column=column)
            column += 1

        self.__elements[title] = text_box
        return text_box

    @staticmethod
    def __replace_text(element: teek.Entry, value: str):
        if value is None:
            value = ''

        if isinstance(element, teek.Text):
            element.delete(element.start, element.end)
            element.insert(element.start, str(value))
        elif isinstance(element, teek.Entry):
            element.text = str(value)


def set_child_states(frame: teek.Frame, state: str = None, types: List[type] = None):
    if state is None:
        state = 'normal'
    for child in frame.winfo_children():
        if isinstance(child, teek.Frame):
            set_child_states(child, state, types)
        else:
            if types is None or any(
                isinstance(child, selected_type) for selected_type in types
            ):
                try:
                    child.config['state'] = state
                except teek.TclError:
                    continue
                except KeyError:
                    if state == 'normal':
                        child.state.discard('disabled')
                    else:
                        child.state.add(state)
