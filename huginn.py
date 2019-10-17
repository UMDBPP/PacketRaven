import logging
import os
import tkinter
from datetime import datetime
from tkinter import filedialog, messagebox

import geojson
import numpy
import simplekml
from geojson import Point, FeatureCollection, Feature, LineString

from huginn import radio, tracks, BALLOON_CALLSIGNS


class HuginnGUI:
    def __init__(self):
        self.main_window = tkinter.Tk()
        self.main_window.title('huginn main')

        self.connections = {}

        self.running = False
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
        self.elements['log_file'].insert(0, f'huginn_log_{datetime.now():%Y%m%dT%H%M%S}.txt')
        log_file_button = tkinter.Button(self.frames['top'], text='...', command=self.__select_log_file)
        log_file_button.grid(row=self.last_row, column=2)

        self.__add_entry_box(self.frames['top'], title='output_file', width=45)
        self.elements['output_file'].insert(0, f'huginn_output_{datetime.now():%Y%m%dT%H%M%S}.kml')
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
            radio_port = radio.port()
        except OSError:
            radio_port = ''

        self.replace_text(self.elements['port'], radio_port)

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
                                            defaultextension='.kml', filetypes=[('Keyhole Markup Language', '*.kml')])
        if path != '':
            self.replace_text(self.elements['output_file'], path)

    def toggle(self):
        if self.running:
            self.connections['radio'].close()
            logging.info(f'Closed port {self.connections["radio"].serial_port}')

            for element in self.frames['bottom'].winfo_children():
                element.configure(state=tkinter.DISABLED)

            self.toggle_text.set('Start')
            self.running = False
        else:
            try:
                self.serial_port = self.elements['port'].get()

                if self.serial_port is '':
                    serial_port = radio.port()
                    self.replace_text(self.elements['port'], serial_port)

                log_filename = self.elements['log_file'].get()
                logging.basicConfig(filename=log_filename, level=logging.INFO,
                                    datefmt='%Y-%m-%d %H:%M:%S', format='[%(asctime)s] %(levelname)s: %(message)s')
                console = logging.StreamHandler()
                console.setLevel(logging.DEBUG)
                logging.getLogger('').addHandler(console)

                self.connections['radio'] = radio.Radio(self.serial_port)
                self.serial_port = self.connections['radio'].serial_port
                logging.info(f'Opened port {self.serial_port}')

                for element in self.frames['bottom'].winfo_children():
                    element.configure(state=tkinter.ACTIVE)

                self.toggle_text.set('Stop')
                self.running = True

                self.run()
            except Exception as error:
                messagebox.showerror('Initialization Error', error)

    def run(self):
        parsed_packets = self.connections['radio'].read()

        for parsed_packet in parsed_packets:
            callsign = parsed_packet['callsign']

            if callsign in self.packet_tracks:
                if parsed_packet in self.packet_tracks[callsign]:
                    logging.debug(f'Received duplicate packet: {parsed_packet}')
                else:
                    self.packet_tracks[callsign].append(parsed_packet)
            else:
                logging.debug(f'Starting new packet track from current packet: {parsed_packet}')
                self.packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])

            message = f'{parsed_packet}'
            packet_track = self.packet_tracks[callsign]

            if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                message = f'{message} ascent_rate={packet_track.ascent_rate} ground_speed={packet_track.ground_speed} seconds_to_impact={packet_track.seconds_to_impact}'

                if callsign in BALLOON_CALLSIGNS:
                    self.replace_text(self.elements['longitude'], packet_track.longitude)
                    self.replace_text(self.elements['latitude'], packet_track.latitude)
                    self.replace_text(self.elements['altitude'], packet_track.altitude)
                    self.replace_text(self.elements['ground_speed'], packet_track.ground_speed)
                    self.replace_text(self.elements['ascent_rate'], packet_track.ascent_rate)

                    packet_deltas = numpy.diff(numpy.array(packet_track.packets))
                    ascent_rates = [0] + [packet_delta.ascent_rate for packet_delta in packet_deltas]
                    ground_speeds = [0] + [packet_delta.ground_speed for packet_delta in packet_deltas]

                    output_filename = self.elements['output_file'].get()
                    extension = os.path.splitext(output_filename)[1]

                    if extension == '.kml':
                        kml = simplekml.Kml()
                        for packet in packet_track.packets:
                            kml.newpoint(name=f'{packet.time:%Y%m%d%H%M%S}', coords=packet.coordinates)
                        kml.newlinestring(name=callsign,
                                          coords=[packet.coordinates for packet in packet_track.packets])
                        kml.save(output_filename)
                    elif extension == '.geojson':
                        features = FeatureCollection([Feature(geometry=Point(packet.coordinates),
                                                              properties={'time': f'{packet.time:%Y%m%d%H%M%S}',
                                                                          'callsign': callsign,
                                                                          'altitude': packet.altitude,
                                                                          'ascent_rate': ascent_rates[packet_index],
                                                                          'ground_speed': ground_speeds[packet_index]})
                                                      for packet_index, packet in enumerate(packet_track.packets)] + [
                                                         Feature(geometry=LineString([packet.coordinates for packet in
                                                                                      packet_track.packets]),
                                                                 properties={'callsign': callsign,
                                                                             'altitude': packet_track.altitude,
                                                                             'ascent_rate': packet_track.ascent_rate,
                                                                             'ground_speed': packet_track.ground_speed,
                                                                             'seconds_to_impact': packet_track.seconds_to_impact})])
                        geojson.dump(features, output_filename)

            logging.info(message)

        if self.running:
            self.main_window.after(1000, self.run)

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
