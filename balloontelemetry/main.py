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
