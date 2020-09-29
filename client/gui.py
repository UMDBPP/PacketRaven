from datetime import datetime
import logging
from pathlib import Path
import re
import tkinter
from tkinter import filedialog, messagebox, simpledialog

from client import DEFAULT_INTERVAL_SECONDS
from packetraven.connections import APRSPacketDatabaseTable, APRSPacketRadio, APRSPacketTextFile, APRSfiConnection, \
    next_available_port
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger
from packetraven.writer import write_aprs_packet_tracks

LOGGER = get_logger('packetraven')

DESKTOP_PATH = Path('~').expanduser() / 'Desktop'


class PacketRavenGUI:
    def __init__(self, callsigns: [str] = None, log_filename: str = None, output_filename: str = None,
                 interval_seconds: int = None, **kwargs):
        self.main_window = tkinter.Tk()
        self.main_window.title('packetraven main')

        self.callsigns = callsigns

        self.log_filename = log_filename if log_filename is not None else DESKTOP_PATH / f'packetraven_log_' \
                                                                                         f'{datetime.now():%Y%m%dT%H%M%S}.txt'
        self.output_filename = output_filename if output_filename is not None else DESKTOP_PATH / f'packetraven_output_' \
                                                                                                  f'{datetime.now():%Y%m%dT%H%M%S}.geojson'

        self.interval_seconds = interval_seconds if interval_seconds is not None else DEFAULT_INTERVAL_SECONDS

        self.configuration = {
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

        for section_name, section in self.configuration.items():
            section.update({
                key: value for key, value in kwargs.items() if key in section
            })

        self.database = None
        self.connections = []

        self.__active = False
        self.packet_tracks = {}

        self.frames = {}
        self.elements = {}
        self.last_row = 0

        self.frames['configuration'] = tkinter.Frame(self.main_window)
        self.frames['configuration'].pack()

        self.frames['controls'] = tkinter.Frame(self.main_window)
        self.frames['controls'].pack()

        self.frames['separator'] = tkinter.Frame(height=2, bd=1, relief=tkinter.SUNKEN)
        self.frames['separator'].pack(fill=tkinter.X, padx=5, pady=5)

        self.frames['data'] = tkinter.Frame(self.main_window)
        self.frames['data'].pack()

        self.__add_entry_box(self.frames['configuration'], 'callsigns', width=45)
        if self.callsigns is not None:
            self.callsigns = self.callsigns.upper()
            self.elements['callsigns'].insert(0, self.callsigns)

        self.__add_entry_box(self.frames['configuration'], 'serial_port')

        self.__add_entry_box(self.frames['configuration'], title='log_file', width=45)
        self.elements['log_file'].insert(0, self.log_filename)
        log_file_button = tkinter.Button(self.frames['configuration'], text='...', command=self.__select_log_file)
        log_file_button.grid(row=self.last_row, column=2)

        self.__add_entry_box(self.frames['configuration'], title='output_file', width=45)
        self.elements['output_file'].insert(0, self.output_filename)
        output_file_button = tkinter.Button(self.frames['configuration'], text='...', command=self.__select_output_file)
        output_file_button.grid(row=self.last_row, column=2)

        self.toggle_text = tkinter.StringVar()
        self.toggle_text.set('Start')
        toggle_button = tkinter.Button(self.frames['controls'], textvariable=self.toggle_text, command=self.toggle)
        toggle_button.grid(row=self.last_row + 1, column=1)
        self.last_row += 1

        self.__add_text_box(self.frames['data'], title='longitude', units='°')
        self.__add_text_box(self.frames['data'], title='latitude', units='°')
        self.__add_text_box(self.frames['data'], title='altitude', units='m')
        self.__add_text_box(self.frames['data'], title='ground_speed', units='m/s')
        self.__add_text_box(self.frames['data'], title='ascent_rate', units='m/s')

        for element in self.frames['data'].winfo_children():
            element.configure(state=tkinter.DISABLED)

        serial_port = self.configuration['radio']['serial_port']
        if serial_port is None:
            try:
                serial_port = next_available_port()
                self.replace_text(self.elements['serial_port'], serial_port)
                self.configuration['radio']['serial_port'] = serial_port
            except OSError:
                LOGGER.debug(f'could not automatically determine radio serial port')

        self.main_window.mainloop()

    def __add_text_box(self, frame: tkinter.Frame, title: str, units: str = None, row: int = None, entry: bool = False,
                       width: int = 10):
        if row is None:
            row = self.last_row + 1

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

        self.last_row = row

        self.elements[title] = element

    def __add_entry_box(self, frame: tkinter.Frame, title: str, row: int = None, width: int = 10):
        self.__add_text_box(frame, title, row=row, entry=True, width=width)

    def __select_log_file(self):
        filename = Path(self.elements['log_file'].get()).stem
        path = filedialog.asksaveasfilename(title='PacketRaven log location...', initialfile=filename,
                                            defaultextension='.txt', filetypes=[('Text', '*.txt')])

        if path != '':
            self.replace_text(self.elements['log_file'], path)

    def __select_output_file(self):
        filename = Path(self.elements['output_file'].get()).stem
        path = filedialog.asksaveasfilename(title='PacketRaven output location...', initialfile=filename,
                                            defaultextension='.kml',
                                            filetypes=[('GeoJSON', '*.geojson'), ('Keyhole Markup Language', '*.kml')])
        if path != '':
            self.replace_text(self.elements['output_file'], path)

    def toggle(self):
        if self.active:
            for connection in self.connections:
                connection.close()

                if type(connection) is APRSPacketRadio:
                    LOGGER.info(f'closing port {connection.location}')

            LOGGER.info(f'closed {len(self.connections)} connections')

            for element in self.frames['data'].winfo_children():
                element.configure(state=tkinter.DISABLED)

            for element in self.frames['configuration'].winfo_children():
                element.configure(state=tkinter.NORMAL)

            self.toggle_text.set('Start')
            self.__active = False
            self.connections = []

            logging.shutdown()
        else:
            log_filename = self.elements['log_file'].get()
            get_logger(LOGGER.name, log_filename)

            callsigns = self.elements['callsigns'].get()
            if callsigns != '':
                callsigns = [callsign.strip().upper() for callsign in re.split(',* ', callsigns.strip('"'))]
                self.callsigns = callsigns
            self.replace_text(self.elements['callsigns'], ', '.join(callsigns))
            self.elements['callsigns'].configure(state=tkinter.DISABLED)

            try:
                connection_errors = []

                radio_port = self.elements['serial_port'].get()
                if radio_port == '':
                    radio_port = self.configuration['radio']['serial_port']
                    if radio_port is None:
                        try:
                            radio_port = next_available_port()
                            self.replace_text(self.elements['serial_port'], radio_port)
                        except Exception as error:
                            connection_errors.append(f'USB - {error}')
                            LOGGER.error(f'{error.__class__.__name__} - {error}')
                            radio_port = None
                self.elements['serial_port'].configure(state=tkinter.DISABLED)

                if radio_port is not None:
                    if 'txt' in radio_port:
                        try:
                            text_file = APRSPacketTextFile(radio_port)
                            LOGGER.info(f'reading file {text_file.location}')
                            self.connections.append(text_file)
                        except Exception as error:
                            connection_errors.append(f'file - {error}')
                            LOGGER.error(f'{error.__class__.__name__} - {error}')
                    else:
                        try:
                            radio = APRSPacketRadio(radio_port)
                            LOGGER.info(f'opened port {radio.location}')
                            radio_port = radio.location
                            self.connections.append(radio)
                        except Exception as error:
                            connection_errors.append(f'serial ports - {error}')
                            LOGGER.error(f'{error.__class__.__name__} - {error}')
                self.configuration['radio']['serial_port'] = radio_port

                api_key = self.configuration['aprs_fi']['api_key']
                if api_key is None:
                    api_key = simpledialog.askstring('APRS.fi API Key', 'enter API key for https://aprs.fi',
                                                     parent=self.main_window, show='*')
                try:
                    aprs_api = APRSfiConnection(self.callsigns, api_key=api_key)
                    LOGGER.info(f'established connection to {aprs_api.location}')
                    self.connections.append(aprs_api)
                    self.configuration['aprs_fi']['api_key'] = api_key
                except Exception as error:
                    connection_errors.append(f'aprs.fi - {error}')
                    LOGGER.error(f'{error.__class__.__name__} - {error}')

                if 'database' in self.configuration and self.configuration['database']['hostname'] is not None:
                    ssh_tunnel_kwargs = {}
                    if 'ssh_tunnel' in self.configuration:
                        ssh_hostname = self.configuration['ssh_tunnel']['ssh_hostname']
                        if ssh_hostname is not None:
                            ssh_tunnel_kwargs.update(self.configuration['ssh_tunnel'])
                            if '@' in ssh_hostname:
                                ssh_tunnel_kwargs['ssh_username'], ssh_tunnel_kwargs['ssh_hostname'] = ssh_hostname.split('@',
                                                                                                                          1)
                            if 'ssh_username' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_username'] is None:
                                ssh_tunnel_kwargs['ssh_username'] = simpledialog.askstring('SSH Tunnel Username',
                                                                                           'enter SSH username for tunnel',
                                                                                           parent=self.main_window)
                            if 'ssh_password' not in ssh_tunnel_kwargs or ssh_tunnel_kwargs['ssh_password'] is None:
                                ssh_tunnel_kwargs['ssh_password'] = simpledialog.askstring('SSH Tunnel Password',
                                                                                           'enter SSH password for tunnel',
                                                                                           parent=self.main_window, show='*')

                    database_kwargs = self.configuration['database']
                    if 'username' not in database_kwargs or database_kwargs['username'] is None:
                        database_kwargs['username'] = simpledialog.askstring('Database Username',
                                                                             'enter database username',
                                                                             parent=self.main_window)
                    if 'password' not in database_kwargs or database_kwargs['password'] is None:
                        database_kwargs['password'] = simpledialog.askstring('Database Password',
                                                                             'enter database password',
                                                                             parent=self.main_window, show='*')

                    try:
                        self.database = APRSPacketDatabaseTable(callsigns=callsigns, **database_kwargs, **ssh_tunnel_kwargs)
                        LOGGER.info(f'connected to {self.database.location}')
                        self.connections.append(self.database)
                        self.configuration['database'].update(database_kwargs)
                        self.configuration['ssh_tunnel'].update(ssh_tunnel_kwargs)
                    except Exception as error:
                        connection_errors.append(f'database - {error}')
                else:
                    self.database = None

                connection_errors = '\n'.join(str(error) for error in connection_errors)
                if len(self.connections) == 0:
                    raise ConnectionError(f'no connections started\n{connection_errors}')

                LOGGER.info(f'opened {len(self.connections)} connections')

                for element in self.frames['configuration'].winfo_children():
                    element.configure(state=tkinter.DISABLED)

                for element in self.frames['data'].winfo_children():
                    element.configure(state=tkinter.NORMAL)

                self.toggle_text.set('Stop')
                self.__active = True
            except Exception as error:
                messagebox.showerror('PacketRaven Error', error)
                self.__active = False
                for element in self.frames['configuration'].winfo_children():
                    element.configure(state=tkinter.NORMAL)

            self.run()

    @property
    def active(self) -> bool:
        return self.__active

    @active.setter
    def active(self, active: bool):
        if active is not self.active:
            self.toggle()

    def run(self):
        if self.active:
            LOGGER.debug(f'receiving packets from {len(self.connections)} source(s)')

            parsed_packets = []
            for connection in self.connections:
                parsed_packets.extend(connection.packets)

            LOGGER.debug(f'received {len(parsed_packets)} packets')

            if len(parsed_packets) > 0:
                for parsed_packet in parsed_packets:
                    callsign = parsed_packet['callsign']

                    if callsign in self.packet_tracks:
                        if parsed_packet not in self.packet_tracks[callsign]:
                            self.packet_tracks[callsign].append(parsed_packet)
                        else:
                            LOGGER.debug(f'skipping duplicate packet: {parsed_packet}')
                            continue
                    else:
                        self.packet_tracks[callsign] = APRSTrack(callsign, [parsed_packet])
                        LOGGER.debug(f'started tracking {callsign:8}')

                    packet_track = self.packet_tracks[callsign]

                    LOGGER.info(f'new packet from {parsed_packet.source.location}: {parsed_packet}')

                    if self.database is not None:
                        LOGGER.info(f'sending packet to {self.database.location}')
                        self.database.insert([parsed_packet])

                    if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                        coordinates = packet_track.coordinates[-1]
                        ascent_rate = packet_track.ascent_rate[-1]
                        ground_speed = packet_track.ground_speed[-1]
                        seconds_to_impact = packet_track.seconds_to_impact

                        LOGGER.info(f'{callsign:8} ascent rate      : {ascent_rate} m/s')
                        LOGGER.info(f'{callsign:8} ground speed     : {ground_speed} m/s')
                        if seconds_to_impact >= 0:
                            LOGGER.info(f'{callsign:8} estimated landing: {seconds_to_impact} s')

                        if callsign in self.callsigns:
                            self.replace_text(self.elements['longitude'], coordinates[0])
                            self.replace_text(self.elements['latitude'], coordinates[1])
                            self.replace_text(self.elements['altitude'], coordinates[2])
                            self.replace_text(self.elements['ground_speed'], ground_speed)
                            self.replace_text(self.elements['ascent_rate'], ascent_rate)

                output_filename = self.elements['output_file'].get()
                if output_filename != '':
                    write_aprs_packet_tracks(self.packet_tracks.values(), output_filename)

            if self.active:
                self.main_window.after(self.interval_seconds * 1000, self.run)

    @staticmethod
    def replace_text(element, value):
        if type(element) is tkinter.Text:
            start_index = '1.0'
        else:
            start_index = 0

        element.delete(start_index, tkinter.END)
        element.insert(start_index, value)
