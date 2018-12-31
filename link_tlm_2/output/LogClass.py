
"""
/* Link Telemetry v2.0 "Mobile"

   Copyright (c) 2015-2017 University of Maryland Space Systems Lab
   NearSpace Balloon Payload Program

   Written by Nicholas Rossomando
   2015-04-11

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:

   The above copyright notice and this permission notice shall be included in all
   copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
   SOFTWARE.

   GroundTrack.py:

   Declares ground track container & handler class. Takes over derived quantity
   calculation from Packet itself; also does a whole lot more quantities. Also
   separates out ground tracks from different callsigns.
*/
"""

import time

class Log:

    """
    Sets up the GroundTrack class with all vars and initial conditions.
    """

    def __init__(self, filename):
        self.filename = filename  # Type: String. Logfile path location
        self.logfile   # Logfile, defined later
        self.logOpen = False # Type: Bool. Is log open?

    def getTS(self):
        """
        Gets the time stamp in string format
        """
        TS = time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime())
        return TS

    def openLog(self):
        """
        Opens log and sets the logOpen var to true
        :return:
        logOpen (by ref)
        """

        self.logfile = open(self.filename,'a')  # Opens the logfile in append mode

        self.logOpen = True

        self.logfile.write('LOG BEGINNING ON ')
        self.logfile.write(self.getTS())  # Writes the timestamp at the top of the log
        self.logfile.write('\n \n')

    def log(self):
        """
        Adds a timestamp to a log
        :return:
        None
        """
        if self.logOpen == True:
            self.logfile.write('LOGGED AT ')
            self.logfile.write(self.getTS())  # Writes in the current time
            self.logfile.write('\n')

    def closeLog(self):
        self.logfile.close()
        self.logOpen = False
