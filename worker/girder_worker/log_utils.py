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


def setupLogger(config):
    level = getattr(logging, config.get('logging', 'level').upper())
    logger = logging.getLogger('girder_worker')
    logger.setLevel(level)

    handler = StdOutHandler()
    formatter = logging.Formatter(config.get('logging', 'format'))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
