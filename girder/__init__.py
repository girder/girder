#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import logging.handlers
import os

from girder.constants import ROOT_DIR, MAX_LOG_SIZE, LOG_BACKUP_COUNT


class LogLevelFilter(object):
    """
    Filter log records based on whether they are between a min and max level.
    """
    def __init__(self, min, max):
        self.minLevel = min
        self.maxLevel = max

    def filter(self, logRecord):
        level = logRecord.levelno
        return level <= self.maxLevel and level >= self.minLevel


def _setupLogger():
    """
    Sets up the girder logger.
    """
    logger = logging.getLogger('girder')
    logger.setLevel(logging.DEBUG)

    eh = logging.handlers.RotatingFileHandler(
        os.path.join(ROOT_DIR, 'logs', 'error.log'), maxBytes=MAX_LOG_SIZE,
        backupCount=LOG_BACKUP_COUNT)
    eh.setLevel(logging.WARNING)
    eh.addFilter(LogLevelFilter(min=logging.WARNING, max=logging.CRITICAL))
    ih = logging.handlers.RotatingFileHandler(
        os.path.join(ROOT_DIR, 'logs', 'info.log'), maxBytes=MAX_LOG_SIZE,
        backupCount=LOG_BACKUP_COUNT)
    ih.setLevel(logging.INFO)
    ih.addFilter(LogLevelFilter(min=logging.DEBUG, max=logging.INFO))

    fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    eh.setFormatter(fmt)
    ih.setFormatter(fmt)

    logger.addHandler(eh)
    logger.addHandler(ih)
    return logger

logger = _setupLogger()
