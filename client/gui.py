from datetime import datetime
import logging
from os import PathLike
from pathlib import Path
import re
import tkinter
from tkinter import filedialog, messagebox, simpledialog
from tkinter.ttk import Combobox, Separator

from dateutil.parser import parse

from client import DEFAULT_INTERVAL_SECONDS
from client.retrieve import retrieve_packets
from packetraven.connections import APRSPacketDatabaseTable, APRSfiConnection, SerialTNC, TextFileTNC, available_ports, \
    next_available_port
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger

LOGGER = get_logger('packetraven')


class PacketRavenGUI:
    def __init__(self, callsigns: [str] = None, log_filename: PathLike = None, output_filename: PathLike = None,
                 interval_seconds: int = None, **kwargs):
        self.__windows = {'main': tkinter.Tk()}
        self.__windows['main'].title('PacketRaven')

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
        self.__last_row = 0

        self.__frames['configuration'] = tkinter.Frame(self.__windows['main'])
        self.__frames['configuration'].pack(side='top', pady=10)

        separator = Separator(self.__windows['main'], orient=tkinter.HORIZONTAL)
        separator.pack(side='top', fill='x', expand=True)

        self.__frames['controls'] = tkinter.Frame(self.__windows['main'])
        self.__frames['controls'].pack(side='top', pady=10)

        configuration_top = tkinter.Frame(self.__frames['configuration'])
        configuration_top.pack(pady=5)
        configuration_bottom = tkinter.Frame(self.__frames['configuration'])
        configuration_bottom.pack(pady=5)

        configuration_left = tkinter.Frame(configuration_top)
        configuration_left.pack(side='left')
        configuration_right = tkinter.Frame(configuration_top)
        configuration_right.pack(side='left')

        self.__add_entry_box(configuration_left, title='callsigns', label='Callsigns', width=30)

        self.__file_selection_option = 'select file...'
        self.__add_combo_box(configuration_left, title='tnc', label='TNC Port / File',
                             options=list(available_ports()) + [self.__file_selection_option], width=20)
        self.__elements['tnc'].bind('<<ComboboxSelected>>', self.__select_tnc)

        self.__add_entry_box(configuration_right, title='start_date', label='Start Date', width=17)
        self.__add_entry_box(configuration_right, title='end_date', label='End Date', width=17)

        self.__add_entry_box(configuration_bottom, title='log_file', label='Log', width=55)
        log_file_button = tkinter.Button(configuration_bottom, text='...', command=self.__select_log_file)
        log_file_button.grid(row=self.__last_row - 1, column=2)

        self.__add_entry_box(configuration_bottom, title='output_file', label='Output', width=55)
        output_file_button = tkinter.Button(configuration_bottom, text='...', command=self.__select_output_file)
        output_file_button.grid(row=self.__last_row - 1, column=2)

        self.__toggle_text = tkinter.StringVar()
        self.__toggle_text.set('Start')
        row = tkinter.Frame(self.__frames['controls'])
        row.pack()
        toggle_button = tkinter.Button(row, textvariable=self.__toggle_text, command=self.toggle)
        toggle_button.pack(fill='both', expand=True)

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

        self.__windows['main'].mainloop()

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
    def tnc(self) -> Path:
        tnc_location = self.__elements['tnc'].get()
        if len(tnc_location) > 0:
            if tnc_location == 'auto':
                try:
                    tnc_location = next_available_port()
                except OSError:
                    LOGGER.warning(f'no open serial ports')
                    tnc_location = None
                self.tnc = tnc_location
            tnc_location = Path(tnc_location)
        else:
            tnc_location = None
        return tnc_location

    @tnc.setter
    def tnc(self, filename: PathLike):
        self.__connection_configuration['tnc']['tnc'] = filename
        if filename is None:
            filename = ''
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
            start_date = f'{start_date:%Y-%m-%s %H:%M:%S}'
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
            end_date = f'{end_date:%Y-%m-%s %H:%M:%S}'
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

    def __add_combo_box(self, frame: tkinter.Frame, title: str, options: [str], **kwargs) -> Combobox:
        width = kwargs['width'] if 'width' in kwargs else None
        combo_box = Combobox(frame, width=width)
        combo_box['values'] = options
        return self.__add_text_box(frame, title, text_box=combo_box, **kwargs)

    def __add_entry_box(self, frame: tkinter.Frame, title: str, **kwargs) -> tkinter.Entry:
        width = kwargs['width'] if 'width' in kwargs else None
        entry_box = tkinter.Entry(frame, width=width)
        return self.__add_text_box(frame, title, text_box=entry_box, **kwargs)

    def __add_text_box(self, frame: tkinter.Frame, title: str, label: str, units: str = None, row: int = None,
                       column: int = None, width: int = 10, text_box: tkinter.Entry = None) -> tkinter.Text:
        if row is None:
            row = self.__last_row
            self.__last_row += 1
        if column is None:
            column = 0

        if label is not None:
            text_label = tkinter.Label(frame, text=label)
            text_label.grid(row=row, column=column)
            column += 1

        if text_box is None:
            text_box = tkinter.Text(frame, width=width, height=1)
        text_box.grid(row=row, column=column)
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

            try:
                connection_errors = []

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
                            LOGGER.error(f'{error.__class__.__name__} - {error}')
                    else:
                        try:
                            serial_tnc = SerialTNC(tnc_location, self.callsigns)
                            LOGGER.info(f'opened port {serial_tnc.location}')
                            self.tnc = serial_tnc.location
                            self.__connections.append(serial_tnc)
                        except Exception as error:
                            connection_errors.append(f'serial TNC - {error}')
                            LOGGER.error(f'{error.__class__.__name__} - {error}')

                api_key = self.__connection_configuration['aprs_fi']['api_key']
                if api_key is None:
                    api_key = simpledialog.askstring('APRS.fi API Key', 'enter API key for https://aprs.fi',
                                                     parent=self.__windows['main'], show='*')
                try:
                    aprs_api = APRSfiConnection(self.callsigns, api_key=api_key)
                    LOGGER.info(f'established connection to {aprs_api.location}')
                    self.__connections.append(aprs_api)
                    self.__connection_configuration['aprs_fi']['api_key'] = api_key
                except Exception as error:
                    connection_errors.append(f'aprs.fi - {error}')
                    LOGGER.error(f'{error.__class__.__name__} - {error}')

                if 'database' in self.__connection_configuration \
                        and self.__connection_configuration['database']['hostname'] is not None:
                    ssh_tunnel_kwargs = {}
                    if 'ssh_tunnel' in self.__connection_configuration:
                        ssh_hostname = self.__connection_configuration['ssh_tunnel']['ssh_hostname']
                        if ssh_hostname is not None:
                            ssh_tunnel_kwargs.update(self.__connection_configuration['ssh_tunnel'])
                            if '@' in ssh_hostname:
                                ssh_tunnel_kwargs['ssh_username'], ssh_tunnel_kwargs['ssh_hostname'] = ssh_hostname.split('@',
                                                                                                                          1)
                            if 'ssh_username' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_username'] is None:
                                ssh_tunnel_kwargs['ssh_username'] = simpledialog.askstring('SSH Tunnel Username',
                                                                                           'enter SSH username for tunnel',
                                                                                           parent=self.__windows['main'])
                            if 'ssh_password' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_password'] is None:
                                ssh_tunnel_kwargs['ssh_password'] = simpledialog.askstring('SSH Tunnel Password',
                                                                                           'enter SSH password for tunnel',
                                                                                           parent=self.__windows['main'],
                                                                                           show='*')

                    database_kwargs = self.__connection_configuration['database']
                    if 'username' not in database_kwargs or database_kwargs['username'] is None:
                        database_kwargs['username'] = simpledialog.askstring('Database Username',
                                                                             'enter database username',
                                                                             parent=self.__windows['main'])
                    if 'password' not in database_kwargs or database_kwargs['password'] is None:
                        database_kwargs['password'] = simpledialog.askstring('Database Password',
                                                                             'enter database password',
                                                                             parent=self.__windows['main'], show='*')

                    try:
                        self.database = APRSPacketDatabaseTable(**database_kwargs, **ssh_tunnel_kwargs,
                                                                callsigns=self.callsigns)
                        LOGGER.info(f'connected to {self.database.location}')
                        self.__connections.append(self.database)
                        self.__connection_configuration['database'].update(database_kwargs)
                        self.__connection_configuration['ssh_tunnel'].update(ssh_tunnel_kwargs)
                    except Exception as error:
                        connection_errors.append(f'database - {error}')
                else:
                    self.database = None

                if len(self.__connections) == 0:
                    connection_errors = '\n'.join(str(error) for error in connection_errors)
                    raise ConnectionError(f'no connections started\n{connection_errors}')

                LOGGER.info(f'listening for packets every {self.interval_seconds}s from {len(self.__connections)} '
                            f'connection(s): {", ".join([connection.location for connection in self.__connections])}')

                disable_children(self.__frames['configuration'])

                for callsign in self.packet_tracks:
                    enable_children(self.__windows[callsign])

                self.__toggle_text.set('Stop')
                self.__active = True
            except Exception as error:
                messagebox.showerror('PacketRaven Error', error)
                self.__active = False
                enable_children(self.__frames['configuration'])

            self.retrieve_packets()
        else:
            for connection in self.__connections:
                connection.close()

                if type(connection) is SerialTNC:
                    LOGGER.info(f'closing port {connection.location}')

            LOGGER.info(f'closed {len(self.__connections)} connections')

            for callsign in self.packet_tracks:
                disable_children(self.__windows[callsign])
            enable_children(self.__frames['configuration'])

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
                    self.__add_text_box(window, title=f'{callsign}.packets', label='Packets')
                    self.__add_text_box(window, title=f'{callsign}.time', label='Last Time', width=19)
                    self.__add_text_box(window, title=f'{callsign}.altitude', label='Last Altitude', units='m')
                    self.__add_text_box(window, title=f'{callsign}.coordinates', label='Last Coordinates', width=19)
                    self.__add_text_box(window, title=f'{callsign}.ascent', label='Last Ascent', units='m')
                    self.__add_text_box(window, title=f'{callsign}.distance', label='Last Distance', units='m')
                    self.__add_text_box(window, title=f'{callsign}.interval', label='Last Interval', units='s')
                    self.__add_text_box(window, title=f'{callsign}.ascent_rate', label='Last Ascent Rate', units='m/s')
                    self.__add_text_box(window, title=f'{callsign}.ground_speed', label='Last Ground Speed', units='m/s')
                    self.__add_text_box(window, title=f'{callsign}.distance_downrange', label='Distance Downrange', units='m')
                    self.__add_text_box(window, title=f'{callsign}.distance_traveled', label='Distance Traveled', units='m')
                    self.__windows[callsign] = window

                packet_track = self.packet_tracks[callsign]
                self.replace_text(self.__elements[f'{callsign}.packets'], len(packet_track))
                self.replace_text(self.__elements[f'{callsign}.time'], packet_track.times[-1])
                self.replace_text(self.__elements[f'{callsign}.altitude'], packet_track.coordinates[-1, 2])
                self.replace_text(self.__elements[f'{callsign}.coordinates'],
                                  ', '.join(str(value) for value in packet_track.coordinates[-1, :2]))
                self.replace_text(self.__elements[f'{callsign}.ascent'], packet_track.ascents[-1])
                self.replace_text(self.__elements[f'{callsign}.distance'], packet_track.distances[-1])
                self.replace_text(self.__elements[f'{callsign}.interval'], packet_track.intervals[-1])
                self.replace_text(self.__elements[f'{callsign}.ascent_rate'], packet_track.ascent_rates[-1])
                self.replace_text(self.__elements[f'{callsign}.ground_speed'], packet_track.ground_speeds[-1])
                self.replace_text(self.__elements[f'{callsign}.distance_downrange'], packet_track.distance_from_start)
                self.replace_text(self.__elements[f'{callsign}.distance_traveled'], packet_track.length)

            if self.active:
                self.__windows['main'].after(self.interval_seconds * 1000, self.retrieve_packets)

    @staticmethod
    def replace_text(element: tkinter.Entry, value: str):
        if isinstance(element, tkinter.Text):
            start_index = '1.0'
        else:
            start_index = 0

        element.delete(start_index, tkinter.END)
        element.insert(start_index, value)


def disable_children(frame: tkinter.Frame):
    for child in frame.winfo_children():
        if isinstance(child, tkinter.Frame):
            disable_children(child)
        else:
            child.configure(state=tkinter.DISABLED)


def enable_children(frame: tkinter.Frame):
    for child in frame.winfo_children():
        if isinstance(child, tkinter.Frame):
            enable_children(child)
        else:
            child.configure(state=tkinter.NORMAL)
