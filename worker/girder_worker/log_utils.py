import logging
import os
import sys


class StdOutHandler(logging.Handler):
    """
    Because we re-bind sys.stdout/stderr dynamically to redirect
    print statements to Girder job logs, we must also dynamically
    refer to sys.stdout dynamically in our custom log handler.
    """

    def emit(self, record):
        sys.stdout.write(self.format(record) + os.linesep)


def setupLogger():
    try:
        level = getattr(logging, os.environ.get('GIRDER_WORKER_LOGGING_LEVEL', 'info').upper())
    except Exception:
        level = logging.INFO
    logger = logging.getLogger('girder_worker')
    logger.setLevel(level)

    handler = StdOutHandler()
    formatter = logging.Formatter(os.environ.get(
        'GIRDER_WORKER_LOGGING_FORMAT', '[%(asctime)s] %(levelname)s: %(message)s'))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
