"""
Log class for custom logging.

__authors__ = ['Quinn Kupec']
"""

import time


class Log:
    def __init__(self, filename):
        self.filename = filename  # Type: String. Logfile path location
        self.logfile  # Logfile, defined later
        self.logOpen = False  # Type: Bool. Is log open?

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

        self.logfile = open(self.filename, 'a')  # Opens the logfile in append mode

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
