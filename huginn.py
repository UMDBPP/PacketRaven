import logging
import os
import tkinter
from datetime import datetime
from tkinter import filedialog, messagebox

from huginn import connections, tracks
from huginn.connections import Radio
from huginn.logger import HuginnLogger
from huginn.writer import write_aprs_packet_tracks

BALLOON_CALLSIGNS = ['W3EAX-10', 'W3EAX-11', 'W3EAX-14']
INTERVAL_SECONDS = 5
DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')


class HuginnGUI:
    def __init__(self):
        self.main_window = tkinter.Tk()
        self.main_window.title('huginn main')

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
        self.elements['log_file'].insert(0, os.path.join(DESKTOP_PATH, f'huginn_log_{datetime.now():%Y%m%dT%H%M%S}.txt'))
        log_file_button = tkinter.Button(self.frames['top'], text='...', command=self.__select_log_file)
        log_file_button.grid(row=self.last_row, column=2)

        self.__add_entry_box(self.frames['top'], title='output_file', width=45)
        self.elements['output_file'].insert(0, os.path.join(DESKTOP_PATH, f'huginn_output_{datetime.now():%Y%m%dT%H%M%S}.geojson'))
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

        try:
            self.serial_port = connections.port()
            self.replace_text(self.elements['port'], self.serial_port)
        except OSError:
            self.serial_port = None

        self.logger = HuginnLogger('huginn')

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
        filename = os.path.splitext(self.elements['log_file'].get())[0]
        path = filedialog.asksaveasfilename(title='Huginn log location...', initialfile=filename,
                                            defaultextension='.txt', filetypes=[('Text', '*.txt')])

        if path != '':
            self.replace_text(self.elements['log_file'], path)

    def __select_output_file(self):
        filename = os.path.splitext(self.elements['output_file'].get())[0]
        path = filedialog.asksaveasfilename(title='Huginn output location...', initialfile=filename,
                                            defaultextension='.kml', filetypes=[('GeoJSON', '*.geojson'), ('Keyhole Markup Language', '*.kml')])
        if path != '':
            self.replace_text(self.elements['output_file'], path)

    def toggle(self):
        if self.active:
            for connection in self.connections:
                connection.close()

                if type(connection) is Radio:
                    self.logger.info(f'closing port {connection.serial_port}')

            for element in self.frames['bottom'].winfo_children():
                element.configure(state=tkinter.DISABLED)

            self.toggle_text.set('Start')
            self.active = False
            self.connections = []

            self.logger.info('stopping')
            logging.shutdown()
        else:
            log_filename = self.elements['log_file'].get()
            self.logger.filename = log_filename
            self.logger.info('starting')

            try:
                if self.serial_port is None:
                    self.serial_port = self.elements['port'].get()

                    if self.serial_port == '':
                        try:
                            self.serial_port = connections.port()
                            self.replace_text(self.elements['port'], self.serial_port)
                        except Exception as error:
                            self.logger.error(f'{error.__class__.__name__}: {error}')
                            self.serial_port = None

                if self.serial_port is not None:
                    if 'txt' in self.serial_port:
                        try:
                            text_file = connections.TextFile(self.serial_port)
                            self.connections.append(text_file)
                        except Exception as error:
                            self.logger.error(f'{error.__class__.__name__}: {error}')
                    else:
                        try:
                            radio = connections.Radio(self.serial_port)
                            self.serial_port = radio.serial_port
                            self.logger.info(f'opened port {self.serial_port}')
                            self.connections.append(radio)
                        except Exception as error:
                            self.logger.error(f'{error.__class__.__name__}: {error}')

                try:
                    aprs_api = connections.APRS_fi(BALLOON_CALLSIGNS)
                    self.logger.info(f'established connection to API')
                    self.connections.append(aprs_api)
                except Exception as error:
                    self.logger.error(f'{error.__class__.__name__}: {error}')

                if len(self.connections) == 0:
                    raise ConnectionError('Could not establish connection to APRS packet source.')

                for element in self.frames['bottom'].winfo_children():
                    element.configure(state=tkinter.NORMAL)

                self.toggle_text.set('Stop')
                self.active = True
            except Exception as error:
                messagebox.showerror('Huginn Error', f'{error.__class__.__name__}: {error}')
                self.active = False

            self.run()

    def run(self):
        if self.active:
            self.logger.debug(f'receiving packets from {len(self.connections)} source(s)')

            parsed_packets = []
            for connection in self.connections:
                parsed_packets.extend(connection.packets)

            self.logger.debug(f'received {len(parsed_packets)} packets')

            if len(parsed_packets) > 0:
                for parsed_packet in parsed_packets:
                    callsign = parsed_packet['callsign']

                    if callsign in self.packet_tracks:
                        if parsed_packet not in self.packet_tracks[callsign]:
                            self.packet_tracks[callsign].append(parsed_packet)
                        else:
                            self.logger.debug(f'{callsign:8} - received duplicate packet: {parsed_packet}')
                            continue
                    else:
                        self.packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])
                        self.logger.debug(f'{callsign:8} - started tracking')

                    self.logger.info(f'{callsign:8} - received new packet: {parsed_packet}')
                    packet_track = self.packet_tracks[callsign]

                    if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                        coordinates = packet_track.coordinates[-1]
                        ascent_rate = packet_track.ascent_rate[-1]
                        ground_speed = packet_track.ground_speed[-1]
                        seconds_to_impact = packet_track.seconds_to_impact

                        self.logger.info(f'{callsign:8} - Ascent rate (m/s): {ascent_rate}')
                        self.logger.info(f'{callsign:8} - Ground speed (m/s): {ground_speed}')
                        if seconds_to_impact >= 0:
                            self.logger.info(f'{callsign:8} - Estimated time until landing (s): {seconds_to_impact}')

                        if callsign in BALLOON_CALLSIGNS:
                            self.replace_text(self.elements['longitude'], coordinates[0])
                            self.replace_text(self.elements['latitude'], coordinates[1])
                            self.replace_text(self.elements['altitude'], coordinates[2])
                            self.replace_text(self.elements['ground_speed'], ground_speed)
                            self.replace_text(self.elements['ascent_rate'], ascent_rate)

                output_filename = self.elements['output_file'].get()
                if output_filename != '':
                    write_aprs_packet_tracks(self.packet_tracks.values(), output_filename)

            if self.active:
                self.main_window.after(INTERVAL_SECONDS * 1000, self.run)

    @staticmethod
    def replace_text(element, value):
        if type(element) is tkinter.Text:
            start_index = '1.0'
        else:
            start_index = 0

        element.delete(start_index, tkinter.END)
        element.insert(start_index, value)


if __name__ == '__main__':
    huginn_gui = HuginnGUI()
