import datetime
import logging
import tkinter
import tkinter.filedialog
import tkinter.messagebox

from huginn import radio, tracks


class HuginnGUI:
    def __init__(self):
        self.main_window = tkinter.Tk()
        self.main_window.title('Huginn Balloon Telemetry')

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

        # try:
        #     self.elements['port'].insert(0, radio.port())
        # except OSError as error:
        #     tkinter.messagebox.showwarning('Startup Warning', error)

        self.main_window.mainloop()

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

    def replace_text(self, element, value):
        if type(element) is tkinter.Text:
            start_index = '1.0'
        else:
            start_index = 0

        element.delete(start_index, tkinter.END)
        element.insert(start_index, value)

    def toggle(self):
        if self.running:
            self.running = False
            self.toggle_text.set('Start')

            for element in self.frames['bottom'].winfo_children():
                element.configure(state=tkinter.DISABLED)
        else:
            self.running = True
            self.toggle_text.set('Stop')

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

                self.radio_connection = radio.Radio(self.serial_port)
                self.serial_port = self.radio_connection.serial_port
                logging.info(f'Opening {self.serial_port}')

                self.run()
            except Exception as error:
                self.running = False
                self.toggle_text.set('Start')
                tkinter.messagebox.showerror('Initialization Error', error)

    def run(self):
        if self.running:
            for element in self.frames['bottom'].winfo_children():
                element.configure(state='normal')

            parsed_packets = self.radio_connection.read()

            for parsed_packet in parsed_packets:
                callsign = parsed_packet['callsign']

                if callsign in self.packet_tracks:
                    self.packet_tracks[callsign].append(parsed_packet)
                else:
                    self.packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])

                longitude, latitude, altitude = self.packet_tracks[callsign].coordinates(z=True)
                ascent_rate = self.packet_tracks[callsign].ascent_rate()
                ground_speed = self.packet_tracks[callsign].ground_speed()
                seconds_to_impact = self.packet_tracks[callsign].seconds_to_impact()

                self.replace_text(self.elements['longitude'], longitude)
                self.replace_text(self.elements['latitude'], latitude)
                self.replace_text(self.elements['altitude'], altitude)
                self.replace_text(self.elements['ground_speed'], ground_speed)
                self.replace_text(self.elements['ascent_rate'], ascent_rate)

                logging.info(
                    f'{parsed_packet} ascent_rate={ascent_rate} ground_speed={ground_speed} seconds_to_impact={seconds_to_impact}')

            self.main_window.after(1000, self.run)
        else:
            logging.info(f'Closing {self.radio_connection.serial_port}')
            self.radio_connection.close()


if __name__ == '__main__':
    huginn_gui = HuginnGUI()
