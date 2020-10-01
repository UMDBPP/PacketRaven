from datetime import datetime
import logging
from os import PathLike
from pathlib import Path
import re
import tkinter
from tkinter import filedialog, messagebox, simpledialog

from client import DEFAULT_INTERVAL_SECONDS
from client.retrieve import retrieve_packets
from packetraven.connections import APRSPacketDatabaseTable, APRSPacketRadio, APRSPacketTextFile, APRSfiConnection, \
    next_available_port
from packetraven.utilities import get_logger

LOGGER = get_logger('packetraven')

DESKTOP_PATH = Path('~').expanduser() / 'Desktop'


class PacketRavenGUI:
    def __init__(self, callsigns: [str] = None, log_filename: PathLike = None, output_filename: PathLike = None,
                 interval_seconds: int = None, **kwargs):
        self.__window = tkinter.Tk()
        self.__window.title('PacketRaven')

        self.interval_seconds = interval_seconds if interval_seconds is not None else DEFAULT_INTERVAL_SECONDS

        self.__connection_configuration = {
            'aprs_fi'   : {
                'api_key': None
            },
            'radio'     : {
                'serial_port': None
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

        self.__frames['configuration'] = tkinter.Frame(self.__window)
        self.__frames['configuration'].pack()

        self.__frames['controls'] = tkinter.Frame(self.__window)
        self.__frames['controls'].pack()

        self.__frames['separator'] = tkinter.Frame(height=2, bd=1, relief=tkinter.SUNKEN)
        self.__frames['separator'].pack(fill=tkinter.X, padx=5, pady=5)

        self.__frames['data'] = tkinter.Frame(self.__window)
        self.__frames['data'].pack()

        self.__add_entry_box(self.__frames['configuration'], 'callsigns', width=45)
        self.__add_entry_box(self.__frames['configuration'], 'serial_port')

        self.__add_entry_box(self.__frames['configuration'], title='log_file', width=45)
        log_file_button = tkinter.Button(self.__frames['configuration'], text='...', command=self.__select_log_file)
        log_file_button.grid(row=self.__last_row, column=2)

        self.__add_entry_box(self.__frames['configuration'], title='output_file', width=45)
        output_file_button = tkinter.Button(self.__frames['configuration'], text='...', command=self.__select_output_file)
        output_file_button.grid(row=self.__last_row, column=2)

        self.__toggle_text = tkinter.StringVar()
        self.__toggle_text.set('Start')
        toggle_button = tkinter.Button(self.__frames['controls'], textvariable=self.__toggle_text, command=self.toggle)
        toggle_button.grid(row=self.__last_row + 1, column=1)
        self.__last_row += 1

        self.__add_text_box(self.__frames['data'], title='longitude', units='°')
        self.__add_text_box(self.__frames['data'], title='latitude', units='°')
        self.__add_text_box(self.__frames['data'], title='altitude', units='m')
        self.__add_text_box(self.__frames['data'], title='ground_speed', units='m/s')
        self.__add_text_box(self.__frames['data'], title='ascent_rate', units='m/s')

        for element in self.__frames['data'].winfo_children():
            element.configure(state=tkinter.DISABLED)

        self.callsigns = callsigns
        self.serial_port = self.__connection_configuration['radio']['serial_port']

        self.log_filename = log_filename
        if self.log_filename is None:
            self.log_filename = DESKTOP_PATH / f'packetraven_log_{datetime.now():%Y%m%dT%H%M%S}.txt'

        self.output_filename = output_filename
        if self.output_filename is None:
            self.output_filename = DESKTOP_PATH / f'packetraven_output_{datetime.now():%Y%m%dT%H%M%S}.geojson'

        self.__window.mainloop()

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
        self.__elements['callsigns'].insert(0, callsigns)

    @property
    def serial_port(self) -> str:
        serial_port = self.__elements['serial_port'].get()
        if serial_port == 'auto':
            try:
                serial_port = next_available_port()
            except OSError:
                LOGGER.warning(f'no open serial ports')
                serial_port = None
            self.serial_port = serial_port
        return serial_port

    @serial_port.setter
    def serial_port(self, serial_port: str):
        self.__connection_configuration['radio']['serial_port'] = serial_port
        if serial_port is None:
            serial_port = ''
        self.replace_text(self.__elements['serial_port'], serial_port)

    @property
    def log_filename(self) -> Path:
        filename = self.__elements['log_file'].get()
        if len(filename) > 0:
            filename = Path(filename)
        else:
            filename = None
        return filename

    @log_filename.setter
    def log_filename(self, filename: PathLike):
        if filename is not None:
            if not isinstance(filename, Path):
                filename = Path(filename)
            filename = filename.expanduser().resolve()
        else:
            filename = ''
        self.replace_text(self.__elements['log_file'], filename)

    @property
    def output_filename(self) -> Path:
        filename = self.__elements['output_file'].get()
        if len(filename) > 0:
            filename = Path(filename)
        else:
            filename = None
        return filename

    @output_filename.setter
    def output_filename(self, filename: PathLike):
        if filename is not None:
            if not isinstance(filename, Path):
                filename = Path(filename)
            filename = filename.expanduser().resolve()
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

    def __add_text_box(self, frame: tkinter.Frame, title: str, units: str = None, row: int = None, entry: bool = False,
                       width: int = 10):
        if row is None:
            row = self.__last_row + 1

        column = 0

        element_label = tkinter.Label(frame, text=title)
        element_label.grid(row=row, column=column)

        column += 1

        if entry:
            element = tkinter.Entry(frame, width=width)
        else:
            element = tkinter.Text(frame, width=width, height=1)

        element.grid(row=row, column=column)

        column += 1

        if units is not None:
            units_label = tkinter.Label(frame, text=units)
            units_label.grid(row=row, column=column)

        column += 1

        self.__last_row = row

        self.__elements[title] = element

    def __add_entry_box(self, frame: tkinter.Frame, title: str, row: int = None, width: int = 10):
        self.__add_text_box(frame, title, row=row, entry=True, width=width)

    def __select_log_file(self):
        self.log_filename = filedialog.asksaveasfilename(title='PacketRaven log location...',
                                                         initialfile=self.log_filename.stem,
                                                         defaultextension='.txt', filetypes=[('Text', '*.txt')])

    def __select_output_file(self):
        self.output_filename = filedialog.asksaveasfilename(title='PacketRaven output location...',
                                                            initialfile=self.output_filename.stem,
                                                            defaultextension='.kml',
                                                            filetypes=[('GeoJSON', '*.geojson'),
                                                                       ('Keyhole Markup Language', '*.kml')])

    def toggle(self):
        if not self.active:
            if self.log_filename is not None:
                get_logger(LOGGER.name, self.log_filename)

            if self.callsigns is not None:
                LOGGER.info(f'filtering by {len(self.callsigns)} selected callsign(s): {self.callsigns}')

            self.__elements['callsigns'].configure(state=tkinter.DISABLED)

            try:
                connection_errors = []

                radio_port = self.serial_port
                self.__elements['serial_port'].configure(state=tkinter.DISABLED)

                if radio_port is not None:
                    if 'txt' in radio_port:
                        try:
                            text_file = APRSPacketTextFile(radio_port, self.callsigns)
                            LOGGER.info(f'reading file {text_file.location}')
                            self.__connections.append(text_file)
                        except Exception as error:
                            connection_errors.append(f'file - {error}')
                            LOGGER.error(f'{error.__class__.__name__} - {error}')
                    else:
                        try:
                            radio = APRSPacketRadio(radio_port, self.callsigns)
                            LOGGER.info(f'opened port {radio.location}')
                            self.serial_port = radio.location
                            self.__connections.append(radio)
                        except Exception as error:
                            connection_errors.append(f'serial ports - {error}')
                            LOGGER.error(f'{error.__class__.__name__} - {error}')

                api_key = self.__connection_configuration['aprs_fi']['api_key']
                if api_key is None:
                    api_key = simpledialog.askstring('APRS.fi API Key', 'enter API key for https://aprs.fi',
                                                     parent=self.__window, show='*')
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
                                                                                           parent=self.__window)
                            if 'ssh_password' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_password'] is None:
                                ssh_tunnel_kwargs['ssh_password'] = simpledialog.askstring('SSH Tunnel Password',
                                                                                           'enter SSH password for tunnel',
                                                                                           parent=self.__window, show='*')

                    database_kwargs = self.__connection_configuration['database']
                    if 'username' not in database_kwargs or database_kwargs['username'] is None:
                        database_kwargs['username'] = simpledialog.askstring('Database Username',
                                                                             'enter database username',
                                                                             parent=self.__window)
                    if 'password' not in database_kwargs or database_kwargs['password'] is None:
                        database_kwargs['password'] = simpledialog.askstring('Database Password',
                                                                             'enter database password',
                                                                             parent=self.__window, show='*')

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

                connection_errors = '\n'.join(str(error) for error in connection_errors)
                if len(self.__connections) == 0:
                    raise ConnectionError(f'no connections started\n{connection_errors}')

                LOGGER.info(f'opened {len(self.__connections)} connections')

                for element in self.__frames['configuration'].winfo_children():
                    element.configure(state=tkinter.DISABLED)

                for element in self.__frames['data'].winfo_children():
                    element.configure(state=tkinter.NORMAL)

                self.__toggle_text.set('Stop')
                self.__active = True
            except Exception as error:
                messagebox.showerror('PacketRaven Error', error)
                self.__active = False
                for element in self.__frames['configuration'].winfo_children():
                    element.configure(state=tkinter.NORMAL)

            self.retrieve_packets()
        else:
            for connection in self.__connections:
                connection.close()

                if type(connection) is APRSPacketRadio:
                    LOGGER.info(f'closing port {connection.location}')

            LOGGER.info(f'closed {len(self.__connections)} connections')

            for element in self.__frames['data'].winfo_children():
                element.configure(state=tkinter.DISABLED)

            for element in self.__frames['configuration'].winfo_children():
                element.configure(state=tkinter.NORMAL)

            self.__toggle_text.set('Start')
            self.__active = False
            self.__connections = []

            logging.shutdown()

    def retrieve_packets(self):
        if self.active:
            retrieve_packets(self.__connections, self.__packet_tracks, self.database, self.output_filename, LOGGER)
            if self.active:
                self.__window.after(self.interval_seconds * 1000, self.retrieve_packets)

    @staticmethod
    def replace_text(element: tkinter.Entry, value: str):
        if isinstance(element, tkinter.Text):
            start_index = '1.0'
        else:
            start_index = 0

        element.delete(start_index, tkinter.END)
        element.insert(start_index, value)
