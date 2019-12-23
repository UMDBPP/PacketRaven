import logging
import sys
import warnings

DEFAULT_FORMAT = '[%(asctime)s] %(levelname)-8s: %(message)s'


class HuginnLogger:
    def __init__(self, name: str, filename: str = None, file_level: int = logging.DEBUG, stream_level: int = logging.INFO,
                 format: str = DEFAULT_FORMAT):
        """
        Logging object with optional handlers for `stdout`, `stderr`, and a text file.

        :param name: name of logger
        :param filename: path to log file
        :param file_level: level at which to messages to the file
        :param stream_level: level at which to messages to the console
        :param format: format of message
        """

        self.__filename = filename
        self.__file_level = file_level
        self.__stream_level = stream_level
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(logging.DEBUG)

        self.__stream_handler = None
        self.__stream_error_handler = None
        self.__file_handler = None

        self.name = name
        self.format = format

        # check if logger is already configured
        if self.__logger.level == logging.NOTSET and len(self.__logger.handlers) == 0:
            # check for a parent logger
            if '.' in name:
                parent = logging.Logger(name.rsplit('.', 1)[0])
                self.__logger.setLevel(parent.level)
                for handler in parent.handlers:
                    self.__logger.addHandler(handler)
                    if type(handler) is logging.FileHandler:
                        break
                else:
                    self.__set_file_handler()
            else:
                self.__logger.setLevel(logging.DEBUG)
                self.__set_stream_handlers()
                self.__set_file_handler()

    @property
    def format(self) -> str:
        return self.__format

    @format.setter
    def format(self, format: str):
        self.__format = format
        self.__formatter = logging.Formatter(format)
        self.__set_file_handler()
        self.__set_stream_handlers()

    @property
    def handlers(self) -> [logging.Handler]:
        return self.__logger.handlers

    @property
    def filename(self) -> str:
        return self.__filename

    @filename.setter
    def filename(self, filename: str):
        self.__filename = filename
        self.__set_file_handler()

    @property
    def file_level(self) -> int:
        return self.__file_level

    @file_level.setter
    def file_level(self, file_level: int):
        self.__file_level = file_level
        self.__set_file_handler()

    @property
    def stream_level(self) -> int:
        return self.__stream_level

    @stream_level.setter
    def stream_level(self, stream_level: int):
        self.__stream_level = stream_level
        self.__set_stream_handlers()

    def __set_file_handler(self):
        if self.__file_handler is not None:
            self.__logger.removeHandler(self.__file_handler)

        if self.filename is not None:
            self.__file_handler = logging.FileHandler(self.filename)
            self.__file_handler.setFormatter(self.__formatter)
            self.__file_handler.setLevel(self.file_level)
            self.__logger.addHandler(self.__file_handler)

    def __set_stream_handlers(self):
        if self.__stream_handler is not None:
            self.__logger.removeHandler(self.__stream_handler)

        if self.__stream_error_handler is not None:
            self.__logger.removeHandler(self.__stream_error_handler)

        if self.stream_level != logging.NOTSET:
            if self.stream_level <= logging.INFO:
                self.__stream_handler = logging.StreamHandler(sys.stdout)
                self.__stream_handler.setFormatter(self.__formatter)
                self.__stream_handler.setLevel(self.stream_level)
                self.__stream_handler.addFilter(LoggingOutputFilter())
                self.__logger.addHandler(self.__stream_handler)

            self.__stream_error_handler = logging.StreamHandler(sys.stderr)
            self.__stream_error_handler.setFormatter(self.__formatter)
            self.__stream_error_handler.setLevel(max(self.stream_level, logging.WARNING))
            self.__logger.addHandler(self.__stream_error_handler)

    def debug(self, msg: str, *args, **kwargs):
        self.__logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.__logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.__logger.warning(msg, *args, **kwargs)

    def warn(self, msg: str, *args, **kwargs):
        warnings.warn("The 'warn' method is deprecated, use 'warning' instead", DeprecationWarning, 2)
        self.__logger.warn(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.__logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.__logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.__logger.exception(msg, *args, **kwargs)

    def log(self, level: int, msg: str, *args, **kwargs):
        self.__logger.log(level, msg, *args, **kwargs)


class LoggingOutputFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> int:
        return record.levelno in (logging.DEBUG, logging.INFO)
