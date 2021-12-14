import configparser
import logging
from os import PathLike
from pathlib import Path
import sys
from typing import Dict

LOGGER_NAME_LENGTH = 17


def repository_root(path: PathLike = None) -> Path:
    if path is None:
        path = __file__
    if not isinstance(path, Path):
        path = Path(path)
    if path.is_file():
        path = path.parent
    if '.git' in (child.name for child in path.iterdir()) or path == path.parent:
        return path
    else:
        return repository_root(path.parent)


def read_configuration(filename: PathLike) -> Dict[str, str]:
    configuration_file = configparser.ConfigParser()
    configuration_file.read(filename)
    return {
        section_name: {key: value for key, value in section.items()}
        for section_name, section in configuration_file.items()
        if section_name.upper() != 'DEFAULT'
    }


def get_logger(
    name: str,
    log_filename: PathLike = None,
    file_level: int = None,
    console_level: int = None,
    log_format: str = None,
) -> logging.Logger:
    """
    instantiate logger instance

    :param name: name of logger
    :param log_filename: path to log file
    :param file_level: minimum log level to write to log file
    :param console_level: minimum log level to print to console
    :param log_format: logger message format
    :return: instance of a Logger object
    """

    if file_level is None:
        file_level = logging.DEBUG
    if console_level is None:
        console_level = logging.INFO
    logger = logging.getLogger(name)

    # check if logger is already configured
    if logger.level == logging.NOTSET and len(logger.handlers) == 0:
        # check if logger has a parent
        if '.' in name:
            if isinstance(logger.parent, logging.RootLogger):
                for existing_console_handler in [
                    handler
                    for handler in logger.parent.handlers
                    if not isinstance(handler, logging.FileHandler)
                ]:
                    logger.parent.removeHandler(existing_console_handler)
            logger.parent = get_logger(name.rsplit('.', 1)[0])
        else:
            # otherwise create a new split-console logger
            if console_level != logging.NOTSET:
                for existing_console_handler in [
                    handler
                    for handler in logger.handlers
                    if not isinstance(handler, logging.FileHandler)
                ]:
                    logger.removeHandler(existing_console_handler)

                console_output = logging.StreamHandler(sys.stdout)
                console_output.setLevel(console_level)
                logger.addHandler(console_output)

    if log_filename is not None:
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(file_level)
        for existing_file_handler in [
            handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)
        ]:
            logger.removeHandler(existing_file_handler)
        logger.addHandler(file_handler)

    if log_format is None:
        log_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    log_formatter = logging.Formatter(log_format)
    for handler in logger.handlers:
        handler.setFormatter(log_formatter)

    return logger
