import importlib.metadata
import logging
import os

from .utility import config

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError:
    # package is not installed
    __version__ = None

__license__ = 'Apache 2.0'
auditLogger = logging.getLogger('girder_audit')
auditLogger.setLevel(logging.INFO)
auditLogger.propagate = False

if not os.getenv('GIRDER_SPHINX_BUILD'):
    config.loadConfig()  # Populate the config info at import time
