# -*- coding: utf-8 -*-
import unittest.mock

from girder import constants, logger

# Mock the logging methods so that we don't actually write logs to disk,
# and so tests can potentially inspect calls to logging methods.
print(constants.TerminalColor.warning('Mocking Girder log methods.'))
for handler in logger.handlers:
    handler.emit = unittest.mock.MagicMock()
