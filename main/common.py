import json
from datetime import datetime
import logging
from os import path

"""Common functions to be used in modules and classes of Syrabond."""

def log(line, log_type='info'):
    """Wrapper for logging. Writes line to log adding datetime."""
    time_string = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(time_string, line)
    if log_type == 'info':
        logging.info(' {} {}'.format(time_string, line))
    elif log_type == 'error':
        logging.error(' {} {}'.format(time_string, line))
    elif log_type == 'debug':
        logging.debug(' {} {}'.format(time_string, line))
    elif log_type == 'warning':
        logging.warning(' {} {}'.format(time_string, line))


def extract_config(file_path: str) -> dict:

    """
    Opens file and extracting json to dict.
    :rtype: dict
    :param file_path: path to config file
    """
    try:
        with open(file_path, 'r') as f:
            items = json.loads(f.read())
    except Exception as e:
        log(f'Unable to open config file {file_path}: {e}', 'error')
        return {}
    return items


def rewrite_config(file_name, content):
    try:
        with open(dir+file_name, 'w') as f:
            f.write(json.dumps(content, ensure_ascii=False, indent=4, sort_keys=True))
    except Exception as e:
        print(e)
        return False
    return True


logging_levels = {
    'CRITICAL': 50,
    'ERROR': 40,
    'WARNING': 30,
    'INFO': 20,
    'DEBUG': 10
}


dir = path.split(path.dirname(path.abspath(__file__)))[0]

config = extract_config(path.join(dir, 'conf.json'))
log_file = path.join(dir, config.get('logging', {}).get('file', 'log.log'))
log_level = logging_levels.get(config.get('logging', {}).get('level', 'INFO'))
if log_file:
    logging.basicConfig(filename=log_file, level=log_level)