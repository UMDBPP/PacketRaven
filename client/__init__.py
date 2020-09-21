from pathlib import Path

from packetraven.utilities import get_logger

LOGGER = get_logger('packetraven')
DEFAULT_INTERVAL_SECONDS = 5
DESKTOP_PATH = Path('~').expanduser() / 'Desktop'
