from datetime import datetime, timedelta
import logging
from os import PathLike
from pathlib import Path
import re
import tkinter
from tkinter import filedialog, messagebox, simpledialog
from tkinter.ttk import Combobox, Separator
from typing import Callable

from dateutil.parser import parse

from client import DEFAULT_INTERVAL_SECONDS
from client.retrieve import retrieve_packets
from packetraven.connections import APRSDatabaseTable, APRSfi, SerialTNC, TextFileTNC, available_ports, \
    next_available_port
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger

LOGGER = get_logger('packetraven')


class PacketRavenGUI:
    def __init__(self, callsigns: [str] = None, log_filename: PathLike = None, output_filename: PathLike = None,
                 interval_seconds: int = None, **kwargs):
        main_window = tkinter.Tk()
        main_window.title('PacketRaven')
        self.__windows = {'main': main_window}

        self.interval_seconds = interval_seconds if interval_seconds is not None else DEFAULT_INTERVAL_SECONDS

        self.__connection_configuration = {
            'aprs_fi'   : {
                'api_key': None
            },
            'tnc'       : {
                'tnc': None
            },
            'database'  : {
                'hostname': None,
                'database': None,
                'table'   : None,
                'username': None,
                'password': None
            },
            'ssh_tunnel': {
                'ssh_hostname': None,
                'ssh_username': None,
                'ssh_password': None
            }
        }

        for section_name, section in self.__connection_configuration.items():
            section.update({
                key: value for key, value in kwargs.items() if key in section
            })

        self.database = None
        self.__connections = []

        self.__active = False
        self.__packet_tracks = {}

        self.__frames = {}
        self.__elements = {}

        configuration_frame = tkinter.Frame(main_window)
        configuration_frame.grid(row=main_window.grid_size()[1], column=0, pady=10)
        self.__frames['configuration'] = configuration_frame

        start_date_entry = self.__add_entry_box(configuration_frame, title='start_date', label='Start Date', width=22,
                                                sticky='w')
        self.__add_entry_box(configuration_frame, title='end_date', label='End Date', width=22,
                             row=start_date_entry.grid_info()['row'], column=start_date_entry.grid_info()['column'] + 1,
                             sticky='e')

        separator = Separator(configuration_frame, orient=tkinter.HORIZONTAL)
        separator.grid(row=configuration_frame.grid_size()[1], column=0, columnspan=configuration_frame.grid_size()[0] + 1,
                       sticky='ew', pady=10)

        self.__add_entry_box(configuration_frame, title='callsigns', label='Callsigns', width=55, columnspan=3)
        self.__file_selection_option = 'select file...'
        self.__add_combo_box(configuration_frame, title='tnc', label='TNC',
                             options=list(available_ports()) + [self.__file_selection_option], option_select=self.__select_tnc,
                             width=52, columnspan=3, sticky='w')

        separator = Separator(configuration_frame, orient=tkinter.HORIZONTAL)
        separator.grid(row=configuration_frame.grid_size()[1], column=0, columnspan=configuration_frame.grid_size()[0] + 1,
                       sticky='ew', pady=10)

        self.__add_file_box(configuration_frame, title='log_file', file_select=self.__select_log_file, label='Log', width=55,
                            columnspan=3, sticky='w')
        self.__add_file_box(configuration_frame, title='output_file', file_select=self.__select_output_file, label='Output',
                            width=55, columnspan=3, sticky='w')

        separator = Separator(main_window, orient=tkinter.HORIZONTAL)
        separator.grid(row=main_window.grid_size()[1], column=0, sticky='ew')

        control_frame = tkinter.Frame(main_window)
        control_frame.grid(row=main_window.grid_size()[1], column=0, pady=10)
        self.__frames['controls'] = control_frame

        self.__toggle_text = tkinter.StringVar()
        self.__toggle_text.set('Start')
        toggle_button = tkinter.Button(control_frame, textvariable=self.__toggle_text, command=self.toggle)
        toggle_button.grid(row=control_frame.grid_size()[1], column=0, sticky='nsew')

        self.callsigns = callsigns
        self.tnc = self.__connection_configuration['tnc']['tnc']

        if 'start_date' in kwargs:
            self.start_date = kwargs['start_date']
        if 'end_date' in kwargs:
            self.end_date = kwargs['end_date']

        self.log_filename = log_filename
        if self.log_filename is None:
            self.log_filename = Path('~') / 'Desktop'

        self.output_filename = output_filename
        if self.output_filename is None:
            self.output_filename = Path('~') / 'Desktop'

        self.__windows['main'].protocol("WM_DELETE_WINDOW", self.close)

        main_window.mainloop()

    @property
    def callsigns(self) -> [str]:
        callsigns = self.__elements['callsigns'].get()
        if len(callsigns) > 0:
            callsigns = [callsign.strip().upper() for callsign in re.split(',+\ *|\ +', callsigns.strip('"'))]
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
    def tnc(self) -> str:
        tnc_location = self.__elements['tnc'].get().upper()
        if len(tnc_location) > 0:
            if tnc_location.upper() == 'AUTO':
                try:
                    tnc_location = next_available_port()
                except OSError:
                    LOGGER.warning(f'no open serial ports')
                    tnc_location = None
                self.tnc = tnc_location
        else:
            tnc_location = None
        return tnc_location

    @tnc.setter
    def tnc(self, filename: str):
        filename = filename
        self.__connection_configuration['tnc']['tnc'] = filename
        if filename is None:
            filename = ''
        else:
            filename = filename.upper()
        self.replace_text(self.__elements['tnc'], filename)

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
        self.replace_text(self.__elements['start_date'], end_date)

    @property
    def log_filename(self) -> Path:
        filename = self.__elements['log_file'].get()
        if len(filename) > 0:
            filename = Path(filename)
            if filename.expanduser().resolve().is_dir():
                self.log_filename = filename
                filename = self.log_filename
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
        filename = self.__elements['output_file'].get()
        if len(filename) > 0:
            filename = Path(filename)
            if filename.expanduser().resolve().is_dir():
                self.output_filename = filename
                filename = self.output_filename
        else:
            filename = None
        return filename

    @output_filename.setter
    def output_filename(self, filename: PathLike):
        if filename is not None:
            if not isinstance(filename, Path):
                filename = Path(filename)
            if filename.expanduser().resolve().is_dir():
                filename = filename / f'packetraven_output_{datetime.now():%Y%m%dT%H%M%S}.geojson'
        else:
            filename = ''
        self.replace_text(self.__elements['output_file'], filename)

    @property
    def active(self) -> bool:
        return self.__active

    @active.setter
    def active(self, active: bool):
        if active is not self.active:
            self.toggle()

    @property
    def packet_tracks(self) -> {str: APRSTrack}:
        return self.__packet_tracks

    def __select_log_file(self):
        self.log_filename = filedialog.asksaveasfilename(title='Create log file...',
                                                         initialdir=self.log_filename.parent,
                                                         initialfile=self.log_filename.stem,
                                                         defaultextension='.txt',
                                                         filetypes=[('Text', '*.txt')])

    def __select_output_file(self):
        self.output_filename = filedialog.asksaveasfilename(title='Create output file...',
                                                            initialdir=self.output_filename.parent,
                                                            initialfile=self.output_filename.stem,
                                                            defaultextension='.geojson',
                                                            filetypes=[('GeoJSON', '*.geojson'),
                                                                       ('Keyhole Markup Language', '*.kml')])

    def __select_tnc(self, event):
        if event.widget.get() == self.__file_selection_option:
            self.tnc = filedialog.askopenfilename(title='Select TNC text file...', defaultextension='.txt',
                                                  filetypes=[('Text', '*.txt')])

    def __add_combo_box(self, frame: tkinter.Frame, title: str, options: [str], option_select: Callable = None,
                        **kwargs) -> Combobox:
        width = kwargs['width'] if 'width' in kwargs else None
        combo_box = Combobox(frame, width=width)
        combo_box['values'] = options
        if option_select is not None:
            combo_box.bind('<<ComboboxSelected>>', option_select)
        return self.__add_text_box(frame, title, text_box=combo_box, **kwargs)

    def __add_file_box(self, frame: tkinter.Frame, title: str, file_select: Callable, **kwargs) -> tkinter.Entry:
        file_box = self.__add_entry_box(frame, title, **kwargs)
        log_file_button = tkinter.Button(frame, text='...', command=file_select)
        log_file_button.grid(row=file_box.grid_info()['row'],
                             column=file_box.grid_info()['column'] + file_box.grid_info()['columnspan'])
        return file_box

    def __add_entry_box(self, frame: tkinter.Frame, title: str, **kwargs) -> tkinter.Entry:
        width = kwargs['width'] if 'width' in kwargs else None
        entry_box = tkinter.Entry(frame, width=width)
        return self.__add_text_box(frame, title, text_box=entry_box, **kwargs)

    def __add_text_box(self, frame: tkinter.Frame, title: str, label: str, units: str = None, row: int = None,
                       column: int = None, width: int = 10, text_box: tkinter.Entry = None, **kwargs) -> tkinter.Text:
        if row is None:
            row = frame.grid_size()[1]
        if column is None:
            column = 0

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
        if not self.active:
            if self.log_filename is not None:
                get_logger(LOGGER.name, self.log_filename)
            self.__elements['log_file'].configure(state=tkinter.DISABLED)

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
                tnc_location = self.tnc
                self.__elements['tnc'].configure(state=tkinter.DISABLED)

                if tnc_location is not None:
                    if 'txt' in tnc_location:
                        try:
                            text_file_tnc = TextFileTNC(tnc_location, self.callsigns)
                            LOGGER.info(f'reading file {text_file_tnc.location}')
                            self.__connections.append(text_file_tnc)
                        except Exception as error:
                            connection_errors.append(f'file TNC - {error}')
                    else:
                        try:
                            serial_tnc = SerialTNC(tnc_location, self.callsigns)
                            LOGGER.info(f'opened port {serial_tnc.location}')
                            self.tnc = serial_tnc.location
                            self.__connections.append(serial_tnc)
                        except Exception as error:
                            connection_errors.append(f'serial TNC - {error}')

                api_key = self.__connection_configuration['aprs_fi']['api_key']
                if api_key is None:
                    api_key = simpledialog.askstring('APRS.fi API Key', 'enter API key for https://aprs.fi',
                                                     parent=self.__windows['main'], show='*')
                try:
                    aprs_api = APRSfi(self.callsigns, api_key=api_key)
                    LOGGER.info(f'established connection to {aprs_api.location}')
                    self.__connections.append(aprs_api)
                    self.__connection_configuration['aprs_fi']['api_key'] = api_key
                except Exception as error:
                    connection_errors.append(f'aprs.fi - {error}')

                if 'database' in self.__connection_configuration \
                        and self.__connection_configuration['database']['hostname'] is not None:
                    try:
                        ssh_tunnel_kwargs = {}
                        if 'ssh_tunnel' in self.__connection_configuration:
                            ssh_hostname = self.__connection_configuration['ssh_tunnel']['ssh_hostname']
                            if ssh_hostname is not None:
                                ssh_tunnel_kwargs.update(self.__connection_configuration['ssh_tunnel'])
                                if '@' in ssh_hostname:
                                    ssh_tunnel_kwargs['ssh_username'], ssh_tunnel_kwargs['ssh_hostname'] = ssh_hostname.split(
                                        '@', 1)
                                if 'ssh_username' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_username'] is None:
                                    ssh_username = simpledialog.askstring('SSH Tunnel Username',
                                                                          f'enter username for SSH host '
                                                                          f'"{ssh_tunnel_kwargs["ssh_hostname"]}"',
                                                                          parent=self.__windows['main'])
                                    if ssh_username is None or len(ssh_username) == 0:
                                        raise ConnectionError('missing SSH username')
                                    ssh_tunnel_kwargs['ssh_username'] = ssh_username

                                if 'ssh_password' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_password'] is None:
                                    password = simpledialog.askstring('SSH Tunnel Password',
                                                                      f'enter password for SSH user '
                                                                      f'"{ssh_tunnel_kwargs["ssh_username"]}"',
                                                                      parent=self.__windows['main'], show='*')
                                    if password is None or len(password) == 0:
                                        raise ConnectionError('missing SSH password')
                                    ssh_tunnel_kwargs['ssh_password'] = password

                        database_kwargs = self.__connection_configuration['database']
                        if 'username' not in database_kwargs or database_kwargs['username'] is None:
                            database_username = simpledialog.askstring('Database Username',
                                                                       f'enter username for database '
                                                                       f'"{database_kwargs["hostname"]}/'
                                                                       f'{database_kwargs["database"]}"',
                                                                       parent=self.__windows['main'])
                            if database_username is None or len(database_username) == 0:
                                raise ConnectionError('missing database username')
                            database_kwargs['username'] = database_username

                        if 'password' not in database_kwargs or database_kwargs['password'] is None:
                            database_password = simpledialog.askstring('Database Password',
                                                                       f'enter password for database user '
                                                                       f'"{database_kwargs["username"]}"',
                                                                       parent=self.__windows['main'], show='*')
                            if database_password is None or len(database_password) == 0:
                                raise ConnectionError('missing database password')
                            database_kwargs['password'] = database_password

                        self.database = APRSDatabaseTable(**database_kwargs, **ssh_tunnel_kwargs,
                                                          callsigns=self.callsigns)
                        LOGGER.info(f'connected to {self.database.location}')
                        self.__connections.append(self.database)
                        self.__connection_configuration['database'].update(database_kwargs)
                        self.__connection_configuration['ssh_tunnel'].update(ssh_tunnel_kwargs)
                    except ConnectionError as error:
                        connection_errors.append(f'database - {error}')
                        self.database = None
                else:
                    self.database = None

                if len(self.__connections) == 0:
                    connection_errors = '\n'.join(connection_errors)
                    raise ConnectionError(f'no connections started\n{connection_errors}')

                LOGGER.info(f'listening for packets every {self.interval_seconds}s from {len(self.__connections)} '
                            f'connection(s): {", ".join([connection.location for connection in self.__connections])}')

                set_child_states(self.__frames['configuration'], tkinter.DISABLED)

                for callsign in self.packet_tracks:
                    set_child_states(self.__windows[callsign], tkinter.DISABLED)

                self.__toggle_text.set('Stop')
                self.__active = True
            except Exception as error:
                messagebox.showerror(error.__class__.__name__, error)
                if '\n' in str(error):
                    for connection_error in str(error).split('\n'):
                        LOGGER.error(connection_error)
                else:
                    LOGGER.error(error)
                self.__active = False
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

            self.__toggle_text.set('Start')
            self.__active = False
            self.__connections = []

            logging.shutdown()

    def retrieve_packets(self):
        if self.active:
            existing_callsigns = list(self.packet_tracks)
            parsed_packets = retrieve_packets(self.__connections, self.__packet_tracks, self.database, self.output_filename,
                                              self.start_date, self.end_date, logger=LOGGER)

            updated_callsigns = {packet.callsign for packet in parsed_packets}
            for callsign in updated_callsigns:
                if callsign not in existing_callsigns:
                    window = tkinter.Toplevel()
                    window.title(callsign)

                    self.__add_text_box(window, title=f'{callsign}.callsign', label='Callsign', sticky='w')
                    self.replace_text(self.__elements[f'{callsign}.callsign'], callsign)
                    self.__add_text_box(window, title=f'{callsign}.packets', label='Packet #', sticky='w')

                    self.__add_text_box(window, title=f'{callsign}.time', label='Time', width=19, sticky='w',
                                        row=self.__elements[f'{callsign}.callsign'].grid_info()['row'],
                                        column=self.__elements[f'{callsign}.callsign'].grid_info()['column'] + 3, columnspan=2)
                    self.__add_text_box(window, title=f'{callsign}.interval', label='Interval', units='s', sticky='w',
                                        row=self.__elements[f'{callsign}.packets'].grid_info()['row'],
                                        column=self.__elements[f'{callsign}.packets'].grid_info()['column'] + 3)

                    separator = Separator(window, orient=tkinter.HORIZONTAL)
                    separator.grid(row=window.grid_size()[1], column=0, columnspan=7, sticky='ew', pady=10)

                    self.__add_text_box(window, title=f'{callsign}.coordinates', label='Coordinates', width=15, sticky='w',
                                        columnspan=2)
                    self.__add_text_box(window, title=f'{callsign}.distance', label='Distance', units='m', sticky='w')
                    self.__add_text_box(window, title=f'{callsign}.ground_speed', label='Ground Speed', units='m/s',
                                        sticky='w')

                    self.__add_text_box(window, title=f'{callsign}.altitude', label='Altitude', units='m', sticky='w',
                                        row=self.__elements[f'{callsign}.coordinates'].grid_info()['row'],
                                        column=self.__elements[f'{callsign}.coordinates'].grid_info()['column'] + 3)
                    self.__add_text_box(window, title=f'{callsign}.ascent', label='Ascent', units='m', sticky='w',
                                        row=self.__elements[f'{callsign}.distance'].grid_info()['row'],
                                        column=self.__elements[f'{callsign}.distance'].grid_info()['column'] + 3)
                    self.__add_text_box(window, title=f'{callsign}.ascent_rate', label='Ascent Rate', units='m/s',
                                        sticky='w', row=self.__elements[f'{callsign}.ground_speed'].grid_info()['row'],
                                        column=self.__elements[f'{callsign}.ground_speed'].grid_info()['column'] + 3)

                    separator = Separator(window, orient=tkinter.HORIZONTAL)
                    separator.grid(row=window.grid_size()[1], column=0, columnspan=7, sticky='ew', pady=10)

                    self.__add_text_box(window, title=f'{callsign}.distance_downrange', label='Distance Downrange', units='m',
                                        sticky='w')
                    self.__add_text_box(window, title=f'{callsign}.distance_traveled', label='Distance Traveled', units='m',
                                        sticky='w')

                    self.__add_text_box(window, title=f'{callsign}.maximum_altitude', label='Max Altitude', units='m',
                                        sticky='w', row=self.__elements[f'{callsign}.distance_downrange'].grid_info()['row'],
                                        column=self.__elements[f'{callsign}.distance_downrange'].grid_info()['column'] + 3)
                    self.__add_text_box(window, title=f'{callsign}.time_to_ground', label='Time to Ground', units='s',
                                        sticky='w', row=self.__elements[f'{callsign}.distance_traveled'].grid_info()['row'],
                                        column=self.__elements[f'{callsign}.distance_traveled'].grid_info()['column'] + 3)

                    separator = Separator(window, orient=tkinter.VERTICAL)
                    separator.grid(row=0, column=3, rowspan=window.grid_size()[1] + 2, sticky='ns', padx=10)

                    window.protocol("WM_DELETE_WINDOW", window.iconify)

                    self.__windows[callsign] = window

                window = self.__windows[callsign]

                if window.state() == 'iconic':
                    window.deiconify()
                if window.focus_get() is None:
                    window.focus_force()

                set_child_states(window)

                packet_track = self.packet_tracks[callsign]
                self.replace_text(self.__elements[f'{callsign}.packets'], len(packet_track))
                self.replace_text(self.__elements[f'{callsign}.time'], f'{packet_track.times[-1]}')
                self.replace_text(self.__elements[f'{callsign}.altitude'], f'{packet_track.coordinates[-1, 2]:.3f}')
                self.replace_text(self.__elements[f'{callsign}.coordinates'],
                                  ', '.join(f'{value:.3f}' for value in packet_track.coordinates[-1, :2]))
                self.replace_text(self.__elements[f'{callsign}.ascent'], f'{packet_track.ascents[-1]:.2f}')
                self.replace_text(self.__elements[f'{callsign}.distance'], f'{packet_track.distances[-1]:.2f}')
                self.replace_text(self.__elements[f'{callsign}.interval'], f'{packet_track.intervals[-1]:.2f}')
                self.replace_text(self.__elements[f'{callsign}.ascent_rate'], f'{packet_track.ascent_rates[-1]:.2f}')
                self.replace_text(self.__elements[f'{callsign}.ground_speed'], f'{packet_track.ground_speeds[-1]:.2f}')

                self.replace_text(self.__elements[f'{callsign}.distance_downrange'], f'{packet_track.distance_from_start:.2f}')
                self.replace_text(self.__elements[f'{callsign}.distance_traveled'], f'{packet_track.length:.2f}')

                self.replace_text(self.__elements[f'{callsign}.maximum_altitude'],
                                  f'{packet_track.coordinates[:, 2].max():.2f}')

                landing_box = self.__elements[f'{callsign}.time_to_ground']

                if packet_track.time_to_ground >= timedelta(seconds=0):
                    landing_box.configure(state=tkinter.NORMAL)
                    self.replace_text(landing_box, f'{packet_track.time_to_ground / timedelta(seconds=1):.2f}')
                else:
                    self.replace_text(landing_box, '')
                    landing_box.configure(state=tkinter.DISABLED)

                set_child_states(window, tkinter.DISABLED, [tkinter.Text])

            if self.active:
                self.__windows['main'].after(int(self.interval_seconds * 1000), self.retrieve_packets)

    @staticmethod
    def replace_text(element: tkinter.Entry, value: str):
        if isinstance(element, tkinter.Text):
            start_index = '1.0'
        else:
            start_index = 0

        element.delete(start_index, tkinter.END)
        element.insert(start_index, value)

    def close(self):
        if self.active:
            self.toggle()
        self.__windows['main'].destroy()


def set_child_states(frame: tkinter.Frame, state: str = None, types: [type] = None):
    if state is None:
        state = tkinter.NORMAL
    for child in frame.winfo_children():
        if isinstance(child, tkinter.Frame):
            set_child_states(child)
        else:
            if types is None or any(isinstance(child, selected_type) for selected_type in types):
                try:
                    child.configure(state=state)
                except tkinter.TclError:
                    continue
