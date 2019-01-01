"""
Balloon telemetry parsing, display, and logging.

__authors__ = ['Quinn Kupec', 'Zachary Burnett']
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

if __name__ == '__main__':
    json_filename = sys.argv[1]
    kml_filename = sys.argv[2] if len(sys.argv) > 2 else None

    ground_tracks = {}

    # TODO add main code here. Workflow:
    #  1) APRS packet comes in over serial
    #  2) parse raw packet string from serial
    #  3) instantiate new APRSPacket object from raw packet string
    #  4) add new packet to its respective ground track (by callsign)
    #  5) display and log packet
