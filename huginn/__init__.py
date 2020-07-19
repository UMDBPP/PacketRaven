import configparser
import logging
import os
import sys


def read_configuration(filename: str) -> {str: str}:
    configuration_file = configparser.ConfigParser()
    configuration_file.read(filename)
    return {section_name: {key: value for key, value in section.items()} for section_name, section in configuration_file.items() if section_name.upper() != 'DEFAULT'}


def git_head_commit_id(path: str = None) -> str:
    git_directory = os.path.join(repository_root(path), '.git')
    with open(os.path.join(git_directory, 'HEAD')) as reference_file:
        commit_filename = reference_file.read().strip().replace('ref: ', '')
    with open(os.path.join(git_directory, commit_filename)) as commit_file:
        return commit_file.read().strip()


def repository_root(path: str = None) -> str:
    if path is None:
        path = __file__
    if os.path.isfile(path):
        path = os.path.dirname(path)
    return path if '.git' in os.listdir(path) else repository_root(os.path.dirname(path))


CREDENTIALS_FILENAME = os.path.join(repository_root(), 'credentials.config')
LOGGER_NAME_LENGTH = 17


def get_logger(name: str, log_filename: str = None, file_level: int = None, console_level: int = None, log_format: str = None) -> logging.Logger:
    if file_level is None:
        file_level = logging.DEBUG
    if console_level is None:
        console_level = logging.INFO
    logger = logging.getLogger(name)

    # check if logger is already configured
    if logger.level == logging.NOTSET and len(logger.handlers) == 0:
        # check if logger has a parent
        if '.' in name:
            logger.parent = get_logger(name.rsplit('.', 1)[0])
        else:
            # otherwise create a new split-console logger
            logger.setLevel(logging.DEBUG)
            if console_level != logging.NOTSET:
                if console_level <= logging.INFO:
                    class LoggingOutputFilter(logging.Filter):
                        def filter(self, rec):
                            return rec.levelno in (logging.DEBUG, logging.INFO)

                    console_output = logging.StreamHandler(sys.stdout)
                    console_output.setLevel(console_level)
                    console_output.addFilter(LoggingOutputFilter())
                    logger.addHandler(console_output)

                console_errors = logging.StreamHandler(sys.stderr)
                console_errors.setLevel(max((console_level, logging.WARNING)))
                logger.addHandler(console_errors)

    if log_filename is not None:
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(file_level)
        for existing_file_handler in [handler for handler in logger.handlers if type(handler) is logging.FileHandler]:
            logger.removeHandler(existing_file_handler)
        logger.addHandler(file_handler)

    if log_format is None:
        log_format = f'[%(asctime)s] %(name)-{LOGGER_NAME_LENGTH}s %(levelname)-8s: %(message)s'
    log_formatter = logging.Formatter(log_format)
    for handler in logger.handlers:
        handler.setFormatter(log_formatter)

    return logger
