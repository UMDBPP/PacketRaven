from datetime import datetime
import logging
from pathlib import Path
import tkinter
from tkinter import filedialog, messagebox, simpledialog

from packetraven import DEFAULT_CALLSIGNS
from packetraven.connections import APRS_fi, PacketRadio, PacketTextFile, next_available_port
from packetraven.tracks import APRSTrack
from packetraven.utilities import get_logger
from packetraven.writer import write_aprs_packet_tracks
from . import DEFAULT_INTERVAL_SECONDS, DESKTOP_PATH, LOGGER


class PacketRavenGUI:
    def __init__(self, aprs_fi_api_key: str = None, callsigns: [str] = None, skip_serial: bool = False, serial_port: str = None,
                 log_filename: str = None, output_filename: str = None, interval_seconds: int = None):
        self.aprs_fi_api_key = aprs_fi_api_key
        self.callsigns = callsigns if callsigns is not None else DEFAULT_CALLSIGNS
        self.skip_serial = skip_serial
        self.serial_port = serial_port
        self.log_filename = log_filename if log_filename is not None else DESKTOP_PATH / f'packetraven_log_{datetime.now():%Y%m%dT%H%M%S}.txt'
        self.output_filename = output_filename if output_filename is not None else DESKTOP_PATH / f'packetraven_output_' \
                                                                                                  f'{datetime.now():%Y%m%dT%H%M%S}.geojson'
        self.interval_seconds = interval_seconds if interval_seconds is not None else DEFAULT_INTERVAL_SECONDS

        self.main_window = tkinter.Tk()
        self.main_window.title('packetraven main')

        self.connections = []

        self.active = False
        self.packet_tracks = {}

        self.frames = {}
        self.elements = {}
        self.last_row = 0

        self.frames['top'] = tkinter.Frame(self.main_window)
        self.frames['top'].pack()

        self.frames['separator'] = tkinter.Frame(height=2, bd=1, relief=tkinter.SUNKEN)
        self.frames['separator'].pack(fill=tkinter.X, padx=5, pady=5)

        self.frames['bottom'] = tkinter.Frame(self.main_window)
        self.frames['bottom'].pack()

        self.__add_entry_box(self.frames['top'], 'port')

        self.__add_entry_box(self.frames['top'], title='log_file', width=45)
        self.elements['log_file'].insert(0, self.log_filename)
        log_file_button = tkinter.Button(self.frames['top'], text='...', command=self.__select_log_file)
        log_file_button.grid(row=self.last_row, column=2)

        self.__add_entry_box(self.frames['top'], title='output_file', width=45)
        self.elements['output_file'].insert(0, self.output_filename)
        output_file_button = tkinter.Button(self.frames['top'], text='...', command=self.__select_output_file)
        output_file_button.grid(row=self.last_row, column=2)

        self.toggle_text = tkinter.StringVar()
        self.toggle_text.set('Start')
        toggle_button = tkinter.Button(self.frames['top'], textvariable=self.toggle_text, command=self.toggle)
        toggle_button.grid(row=self.last_row + 1, column=1)
        self.last_row += 1

        self.__add_text_box(self.frames['bottom'], title='longitude', units='°')
        self.__add_text_box(self.frames['bottom'], title='latitude', units='°')
        self.__add_text_box(self.frames['bottom'], title='altitude', units='m')
        self.__add_text_box(self.frames['bottom'], title='ground_speed', units='m/s')
        self.__add_text_box(self.frames['bottom'], title='ascent_rate', units='m/s')

        for element in self.frames['bottom'].winfo_children():
            element.configure(state=tkinter.DISABLED)

        if self.serial_port is None:
            try:
                self.serial_port = next_available_port()
                self.replace_text(self.elements['port'], self.serial_port)
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
                                            defaultextension='.kml', filetypes=[('GeoJSON', '*.geojson'), ('Keyhole Markup Language', '*.kml')])
        if path != '':
            self.replace_text(self.elements['output_file'], path)

    def toggle(self):
        if self.active:
            for connection in self.connections:
                connection.close()

                if type(connection) is PacketRadio:
                    LOGGER.info(f'closing port {connection.location}')

            for element in self.frames['bottom'].winfo_children():
                element.configure(state=tkinter.DISABLED)

            self.toggle_text.set('Start')
            self.active = False
            self.connections = []

            LOGGER.info('stopping')
            logging.shutdown()
        else:
            log_filename = self.elements['log_file'].get()
            get_logger(LOGGER.name, log_filename)
            LOGGER.info('starting')

            try:
                if self.serial_port is None:
                    self.serial_port = self.elements['port'].get()

                    if self.serial_port == '':
                        try:
                            self.serial_port = next_available_port()
                            self.replace_text(self.elements['port'], self.serial_port)
                        except Exception as error:
                            LOGGER.exception(f'{error.__class__.__name__} - {error}')
                            self.serial_port = None

                if not self.skip_serial and self.serial_port is not None:
                    if 'txt' in self.serial_port:
                        try:
                            text_file = PacketTextFile(self.serial_port)
                            LOGGER.info(f'reading file {text_file.location}')
                            self.connections.append(text_file)
                        except Exception as error:
                            LOGGER.exception(f'{error.__class__.__name__} - {error}')
                    else:
                        try:
                            radio = PacketRadio(self.serial_port)
                            LOGGER.info(f'opened port {radio.location}')
                            self.serial_port = radio.location
                            self.connections.append(radio)
                        except Exception as error:
                            LOGGER.exception(f'{error.__class__.__name__} - {error}')

                if self.aprs_fi_api_key is None:
                    self.aprs_fi_api_key = simpledialog.askstring('APRS.fi API Key', 'enter API key for https://aprs.fi', parent=self.main_window)

                try:
                    aprs_api = APRS_fi(self.callsigns, api_key=self.aprs_fi_api_key)
                    LOGGER.info(f'established connection to {aprs_api.location}')
                    self.connections.append(aprs_api)
                except Exception as error:
                    LOGGER.exception(f'{error.__class__.__name__} - {error}')

                if len(self.connections) == 0:
                    raise ConnectionError('Could not establish connection to APRS packet source.')

                for element in self.frames['bottom'].winfo_children():
                    element.configure(state=tkinter.NORMAL)

                self.toggle_text.set('Stop')
                self.active = True
            except Exception as error:
                messagebox.showerror('PacketRaven Error', f'{error.__class__.__name__} - {error}')
                self.active = False

            self.run()

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
                            LOGGER.debug(f'{callsign:8} - received duplicate packet: {parsed_packet}')
                            continue
                    else:
                        self.packet_tracks[callsign] = APRSTrack(callsign, [parsed_packet])
                        LOGGER.debug(f'{callsign:8} - started tracking')

                    LOGGER.info(f'{callsign:8} - received new packet: {parsed_packet}')
                    packet_track = self.packet_tracks[callsign]

                    if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                        coordinates = packet_track.coordinates[-1]
                        ascent_rate = packet_track.ascent_rate[-1]
                        ground_speed = packet_track.ground_speed[-1]
                        seconds_to_impact = packet_track.seconds_to_impact

                        LOGGER.info(f'{callsign:8} - Ascent rate (m/s): {ascent_rate}')
                        LOGGER.info(f'{callsign:8} - Ground speed (m/s): {ground_speed}')
                        if seconds_to_impact >= 0:
                            LOGGER.info(f'{callsign:8} - Estimated time until landing (s): {seconds_to_impact}')

                        if callsign in DEFAULT_CALLSIGNS:
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
