import datetime
import sys
import tkinter
import tkinter.filedialog

import logbook

from huginn import radio, packets, parsing, tracks


class HuginnGUI:
    def __init__(self):
        self.main_window = tkinter.Tk()
        self.main_window.title('Huginn Balloon Telemetry')

        self.top_frame = tkinter.Frame(self.main_window)
        self.top_frame.pack()

        self.running = False

        self.packet_tracks = {}

        self.serial_port_label = tkinter.Label(self.top_frame, text='Port:')
        self.serial_port_input = tkinter.Entry(self.top_frame, width=12)
        serial_port = radio.find_port()
        if serial_port is not None:
            self.serial_port_input.insert(0, serial_port)
        self.serial_port_label.grid(row=0, column=0)
        self.serial_port_input.grid(row=0, column=1)

        self.logfile_label = tkinter.Label(self.top_frame, text='Log:')
        self.logfile_input = tkinter.Entry(self.top_frame, width=45)
        self.logfile_input.insert(0, f'huginn_log_{datetime.datetime.now().strftime("%Y%m%dT%H%M%S")}.txt')
        self.logfile_button = tkinter.Button(self.top_frame, text='...', command=self.select_logfile)
        self.logfile_label.grid(row=1, column=0)
        self.logfile_input.grid(row=1, column=1)
        self.logfile_button.grid(row=1, column=2)

        self.start_stop_button_text = tkinter.StringVar()
        self.start_stop_button = tkinter.Button(self.top_frame, textvariable=self.start_stop_button_text,
                                                command=self.start_stop)
        self.start_stop_button_text.set('Start')
        self.start_stop_button.grid(row=2, column=1)

        separator = tkinter.Frame(height=2, bd=1, relief=tkinter.SUNKEN)
        separator.pack(fill=tkinter.X, padx=5, pady=5)

        self.bottom_frame = tkinter.Frame(self.main_window)
        self.bottom_frame.pack()

        self.longitude_label = tkinter.Label(self.bottom_frame, text='Longitude:')
        self.longitude_text = tkinter.Text(self.bottom_frame, width=10, height=1)
        self.longitude_label.grid(row=3, column=0)
        self.longitude_text.grid(row=3, column=1)

        self.latitude_label = tkinter.Label(self.bottom_frame, text='Latitude:')
        self.latitude_text = tkinter.Text(self.bottom_frame, width=10, height=1)
        self.latitude_label.grid(row=4, column=0)
        self.latitude_text.grid(row=4, column=1)

        self.altitude_label = tkinter.Label(self.bottom_frame, text='Altitude:')
        self.altitude_text = tkinter.Text(self.bottom_frame, width=10, height=1)
        self.altitude_units_label = tkinter.Label(self.bottom_frame, text='m')
        self.altitude_label.grid(row=5, column=0)
        self.altitude_text.grid(row=5, column=1)
        self.altitude_units_label.grid(row=5, column=2)

        self.ground_speed_label = tkinter.Label(self.bottom_frame, text='Ground speed:')
        self.ground_speed_text = tkinter.Text(self.bottom_frame, width=10, height=1)
        self.ground_speed_units_label = tkinter.Label(self.bottom_frame, text='m/s')
        self.ground_speed_label.grid(row=6, column=0)
        self.ground_speed_text.grid(row=6, column=1)
        self.ground_speed_units_label.grid(row=6, column=2)

        self.ascent_rate_label = tkinter.Label(self.bottom_frame, text='Ascent rate:')
        self.ascent_rate_text = tkinter.Text(self.bottom_frame, width=10, height=1)
        self.ascent_rate_units_label = tkinter.Label(self.bottom_frame, text='m/s')
        self.ascent_rate_label.grid(row=7, column=0)
        self.ascent_rate_text.grid(row=7, column=1)
        self.ascent_rate_units_label.grid(row=7, column=2)

        for child in self.bottom_frame.winfo_children():
            child.configure(state='disable')

        self.main_window.mainloop()

    def select_logfile(self):
        filename = self.logfile_input.get()
        log_path = tkinter.filedialog.asksaveasfilename(title='Huginn log location...', initialfile=filename,
                                                        filetypes=[('Text', '*.txt')])
        self.logfile_input.insert(0, log_path)

    def start_stop(self):
        if self.running:
            self.running = False
            self.start_stop_button_text.set('Start')
        else:
            self.running = True
            self.start_stop_button_text.set('Stop')
            self.run()

    def run(self):
        log_filename = self.logfile_input.get()
        serial_port = self.serial_port_input.get()

        if serial_port is '':
            serial_port = None

        with radio.connect(serial_port) as radio_connection:
            logbook.FileHandler(log_filename, level='DEBUG', bubble=True).push_application()
            logbook.StreamHandler(sys.stdout, level='INFO', bubble=True).push_application()
            logger = logbook.Logger('Huginn')

            logger.info(f'Opening {radio_connection.name}')

            if self.running:
                for child in self.bottom_frame.winfo_children():
                    child.configure(state='enable')

                raw_packets = radio.get_packets(radio_connection)

                for raw_packet in raw_packets:
                    try:
                        parsed_packet = packets.APRSPacket(raw_packet)
                    except parsing.PartialPacketError as error:
                        parsed_packet = None
                        logger.debug(f'PartialPacketError: {error} ("{raw_packet}")')

                    if parsed_packet is not None:
                        callsign = parsed_packet['callsign']

                        if callsign in self.packet_tracks:
                            self.packet_tracks[callsign].append(parsed_packet)
                        else:
                            self.packet_tracks[callsign] = tracks.APRSTrack(callsign, [parsed_packet])

                        ascent_rate = self.packet_tracks[callsign].ascent_rate()
                        ground_speed = self.packet_tracks[callsign].ground_speed()
                        seconds_to_impact = self.packet_tracks[callsign].seconds_to_impact()

                        logger.info(
                            f'{parsed_packet} ascent_rate={ascent_rate} ground_speed={ground_speed} seconds_to_impact={seconds_to_impact}')

                self.main_window.after(2000, self.run)
            else:
                for child in self.bottom_frame.winfo_children():
                    child.configure(state='disable')

                logger.notice(f'Closing {radio_connection.name}')


if __name__ == '__main__':
    huginn_gui = HuginnGUI()
