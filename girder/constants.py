#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

"""
Constants should be defined here.
"""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_PLUGINS_PACKAGE = 'girder.plugins'
MAX_LOG_SIZE = 1024 * 1024 * 10  # Size in bytes before logs are rotated.
LOG_BACKUP_COUNT = 5


class TerminalColor(object):
    """
    Provides a set of values that can be used to color text in the terminal.
    """
    ERROR = '\033[1;91m'
    SUCCESS = '\033[32m'
    WARNING = '\033[1;33m'
    INFO = '\033[35m'
    ENDC = '\033[0m'

    @staticmethod
    def _color(tag, text):
        return ''.join([tag, text, TerminalColor.ENDC])

    @staticmethod
    def error(text):
        return TerminalColor._color(TerminalColor.ERROR, text)

    @staticmethod
    def success(text):
        return TerminalColor._color(TerminalColor.SUCCESS, text)

    @staticmethod
    def warning(text):
        return TerminalColor._color(TerminalColor.WARNING, text)

    @staticmethod
    def info(text):
        return TerminalColor._color(TerminalColor.INFO, text)


class AssetstoreType:
    """
    All possible assetstore implementation types.
    """
    FILESYSTEM = 0
    GRIDFS = 1
    S3 = 2


class AccessType:
    """
    Represents the level of access granted to a user or group on an
    AccessControlledModel. Having a higher access level on a resource also
    confers all of the privileges of the lower levels.

    Semantically, READ access on a resource means that the user can see all
    the information pertaining to the resource, but cannot modify it.

    WRITE access usually means the user can modify aspects of the resource.

    ADMIN access confers total control; the user can delete the resource and
    also manage permissions for other users on it.
    """
    NONE = -1
    READ = 0
    WRITE = 1
    ADMIN = 2


class SettingKey:
    """
    Core settings should be enumerated here by a set of constants corresponding
    to sensible strings.
    """
    PLUGINS_ENABLED = 'core.plugins_enabled'
    COOKIE_LIFETIME = 'core.cookie_lifetime'
    EMAIL_FROM_ADDRESS = 'core.email_from_address'
    SMTP_HOST = 'core.smtp_host'
