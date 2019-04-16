import datetime
import logging
import tkinter
import tkinter.filedialog
import tkinter.messagebox

import numpy
from matplotlib import pyplot

from huginn import radio, tracks, BALLOON_CALLSIGNS


class HuginnGUI:
    def __init__(self):
        self.windows = {'main': tkinter.Tk()}
        self.windows['main'].title('huginn main')

        self.connections = {}

        self.axes = {}

        self.running = False
        self.packet_tracks = {}

        self.frames = {}
        self.elements = {}
        self.last_row = 0

        self.frames['top'] = tkinter.Frame(self.windows['main'])
        self.frames['top'].pack()

        self.frames['separator'] = tkinter.Frame(height=2, bd=1, relief=tkinter.SUNKEN)
        self.frames['separator'].pack(fill=tkinter.X, padx=5, pady=5)

        self.frames['bottom'] = tkinter.Frame(self.windows['main'])
        self.frames['bottom'].pack()

        self.add_entry_box(self.frames['top'], 'port')

        self.add_entry_box(self.frames['top'], title='logfile', width=45)
        self.elements['logfile'].insert(0, f'huginn_log_{datetime.datetime.now().strftime("%Y%m%dT%H%M%S")}.txt')
        logfile_button = tkinter.Button(self.frames['top'], text='...', command=self.select_logfile)
        logfile_button.grid(row=1, column=2)

        self.toggle_text = tkinter.StringVar()
        self.toggle_text.set('Start')
        toggle_button = tkinter.Button(self.frames['top'], textvariable=self.toggle_text, command=self.toggle)
        toggle_button.grid(row=self.last_row, column=1)
        self.last_row += 1

        self.add_text_box(self.frames['bottom'], title='longitude', units='°')
        self.add_text_box(self.frames['bottom'], title='latitude', units='°')
        self.add_text_box(self.frames['bottom'], title='altitude', units='m')
        self.add_text_box(self.frames['bottom'], title='ground_speed', units='m/s')
        self.add_text_box(self.frames['bottom'], title='ascent_rate', units='m/s')

        for element in self.frames['bottom'].winfo_children():
            element.configure(state=tkinter.DISABLED)

        try:
            radio_port = radio.port()
        except OSError:
            radio_port = ''

        self.replace_text(self.elements['port'], radio_port)

        self.windows['main'].mainloop()

    def add_text_box(self, frame: tkinter.Frame, title: str, units: str = None, row: int = None, entry: bool = False,
                     width: int = 10):
        if row is None:
            row = self.last_row

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

        self.last_row = row + 1

        self.elements[title] = element

    def add_entry_box(self, frame: tkinter.Frame, title: str, row: int = None, width: int = 10):
        self.add_text_box(frame, title, row=row, entry=True, width=width)

    def select_logfile(self):
        filename = self.elements['logfile'].get()
        log_path = tkinter.filedialog.asksaveasfilename(title='Huginn log location...', initialfile=filename,
                                                        filetypes=[('Text', '*.txt')])
        self.replace_text(self.elements['log'], log_path)

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

                log_filename = self.elements['logfile'].get()
                logging.basicConfig(filename=log_filename, level=logging.INFO,
                                    datefmt='%Y-%m-%d %H:%M:%S', format='[%(asctime)s] %(levelname)s: %(message)s')
                console = logging.StreamHandler()
                console.setLevel(logging.DEBUG)
                logging.getLogger('').addHandler(console)

                self.connections['radio'] = radio.Radio(self.serial_port)
                self.serial_port = self.connections['radio'].serial_port
                logging.info(f'Opened port {self.serial_port}')

                if 'plot' in self.windows:
                    self.windows['plot'].clear()
                else:
                    self.windows['plot'] = pyplot.figure(num='huginn plots')

                self.axes['altitude'] = {'axis': self.windows['plot'].add_subplot(1, 2, 1), 'lines': {}}
                self.axes['ascent_rate'] = {'axis': self.windows['plot'].add_subplot(1, 2, 2), 'lines': {}}

                pyplot.show(block=False)

                for element in self.frames['bottom'].winfo_children():
                    element.configure(state='normal')

                self.toggle_text.set('Stop')
                self.running = True

                self.run()
            except Exception as error:
                tkinter.messagebox.showerror('Initialization Error', error)

            self.run()

    def run(self):
        parsed_packets = self.connections['radio'].read()

        for parsed_packet in parsed_packets:
            callsign = parsed_packet['callsign']

            if callsign in self.packet_tracks:
                if parsed_packet not in self.packet_tracks[callsign]:
                    self.packet_tracks[callsign].append(parsed_packet)
                else:
                    logging.debug(f'Received duplicate packet: {parsed_packet}')
            else:
                self.packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])

            message = f'{parsed_packet}'

            if 'longitude' in parsed_packet and 'latitude' in parsed_packet:
                longitude, latitude, altitude = self.packet_tracks[callsign].coordinates()
                ascent_rate = self.packet_tracks[callsign].ascent_rate()
                ground_speed = self.packet_tracks[callsign].ground_speed()
                seconds_to_impact = self.packet_tracks[callsign].seconds_to_impact()
                message += f'ascent_rate={ascent_rate} ground_speed={ground_speed} seconds_to_impact={seconds_to_impact}'

                if callsign in BALLOON_CALLSIGNS:
                    self.replace_text(self.elements['longitude'], longitude)
                    self.replace_text(self.elements['latitude'], latitude)
                    self.replace_text(self.elements['altitude'], altitude)
                    self.replace_text(self.elements['ground_speed'], ground_speed)
                    self.replace_text(self.elements['ascent_rate'], ascent_rate)

            logging.info(message)

            altitude_axis = self.axes['altitude']['axis']
            ascent_rate_axis = self.axes['ascent_rate']['axis']

            if callsign in BALLOON_CALLSIGNS:
                packet_track = self.packet_tracks[callsign]

                packet_track_packets = packet_track.packets

                times = [packet.time for packet in packet_track_packets]
                altitudes = [packet.altitude for packet in packet_track_packets]
                ascent_rates = [0] + [packet_delta.ascent_rate for packet_delta in
                                      numpy.diff(numpy.array(packet_track_packets))]

                if callsign in self.axes['altitude']['lines']:
                    altitude_axis.set_xlim(min(times), max(times))
                    altitude_axis.set_ylim(min(altitudes), max(altitudes))

                    self.axes['altitude']['lines'][callsign].set_xdata(times)
                    self.axes['altitude']['lines'][callsign].set_ydata(altitudes)
                else:
                    self.axes['altitude']['lines'][callsign], = altitude_axis.plot(times, altitudes, '-o')

                if callsign in self.axes['ascent_rate']['lines']:
                    ascent_rate_axis.set_xlim(min(times), max(times))
                    ascent_rate_axis.set_ylim(min(ascent_rates), max(ascent_rates))

                    self.axes['ascent_rate']['lines'][callsign].set_xdata(times)
                    self.axes['ascent_rate']['lines'][callsign].set_ydata(ascent_rates)
                else:
                    self.axes['ascent_rate']['lines'][callsign], = ascent_rate_axis.plot(times, ascent_rates, '-o')

                self.windows['plot'].canvas.draw_idle()

        if self.running:
            self.windows['main'].after(1000, self.run)

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
