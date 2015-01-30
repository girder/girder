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
'''
This module contains functions to install optional components
into the current girder installation.  Note that girder must
be restarted for these changes to take effect.
'''

import os
import urllib2
import tempfile
import tarfile
import shutil
import pip

from girder import constants
from girder.utility.plugin_utilities import getPluginDir


version = constants.VERSION['apiVersion']

# Default download location for optional features
defaultSource = (
    'https://github.com/girder/girder/releases/download/v%s/' % version
)


def fix_path(path):
    '''
    Get an absolute path (while expanding ~).

    :param str path: a filesystem path
    :return: an absolute path
    :rtype: str
    '''
    # first expand ~
    path = os.path.expanduser(path)

    # get the absolute path
    return os.path.abspath(path)


def handle_source(src, dest):
    '''
    Stage a source specification into a temporary directory for processing.
    Returns False if unsuccessful.

    :param str src: source specification (filesystem or url)
    :param str dest: destination path
    :returns: True if success else False
    :rtype: bool
    '''

    try:  # pragma: no cover
        # Try to open as a url
        request = urllib2.urlopen(src)
        download = tempfile.NamedTemporaryFile(suffix='.tgz')
        download.file.write(request.read())
        download.file.flush()
        download.file.seek(0)
        src = download.name
    except (urllib2.URLError, ValueError):
        pass

    src = fix_path(src)
    if os.path.isdir(src):
        # This is already a directory, so copy it.
        pluginName = os.path.split(src)[1]
        dest = os.path.join(dest, pluginName)
        shutil.copytree(src, dest)
        return True

    if os.path.exists(src):
        # Try to open as a tarball.
        try:
            tgz = tarfile.open(src)
            tgz.extractall(dest)
            return True
        except tarfile.ReadError:
            pass

    # Nothing else to try
    return False


def install_web(source=None, force=False):  # pragma: no cover
    '''
    Install the web client from the given source.  If no source
    is present it will install from the current release package
    on Github.

    :param str src: source specification (filesystem or url)
    :param bool force: allow overwriting existing files
    :returns: True if success else False
    :rtype: bool
    '''
    if source is None:
        source = defaultSource + 'girder-web-' + version + '.tar.gz'

    webRoot = os.path.join(constants.STATIC_ROOT_DIR, 'clients', 'web')
    clients = os.path.join(constants.PACKAGE_DIR, 'clients')

    result = None
    if os.path.isdir(clients):
        if force:
            shutil.rmtree(clients)
        else:
            print constants.TerminalColor.warning(
                'Client files already exist at %s, use "force" to overwrite.' %
                constants.STATIC_ROOT_DIR
            )
            return False

    tmp = tempfile.mkdtemp()
    try:
        result = handle_source(source, tmp)
        clients = os.path.join(tmp, 'clients')
        if result and os.path.isdir(clients):
            shutil.copytree(clients, os.path.join(
                constants.PACKAGE_DIR,
                'clients'
            ))
            result = webRoot

    finally:
        shutil.rmtree(tmp)

    return result


def install_plugin(source=None, force=False):
    '''
    Install one or more plugins from the given source.  If no
    source is given, it will install all plugins in the release
    package on Github.  The source provided must be a directory
    or tarball containing one or more directories which
    will be installed as individual plugins.

    :param str src: source specification (filesystem or url)
    :param bool force: allow overwriting existing files
    :returns: a list of plugins that were installed
    :rtype: list
    '''
    if source is None:  # pragma: no cover
        source = defaultSource + 'girder-plugins-' + version + '.tar.gz'

    found = []
    tmp = tempfile.mkdtemp()
    try:
        handle_source(source, tmp)

        plugins = []
        for pth in os.listdir(tmp):
            pth = os.path.join(tmp, pth)
            if os.path.isdir(pth):
                plugins.append(pth)

        for plugin in plugins:
            pluginName = os.path.split(plugin)[1]
            pluginTarget = os.path.join(getPluginDir(), pluginName)

            if os.path.exists(pluginTarget):
                if force:
                    shutil.rmtree(pluginTarget)
                else:
                    print constants.TerminalColor.warning(
                        'A plugin already exists at %s, '
                        'use "force" to overwrite.' % pluginTarget
                    )
                    continue
            found.append(pluginName)
            shutil.copytree(plugin, pluginTarget)
            requirements = os.path.join(pluginTarget, 'requirements.txt')
            if os.path.exists(requirements):  # pragma: no cover
                print constants.TerminalColor.info(
                    'Attempting to install requirements for %s.\n' % pluginName
                )
                if pip.main(['install', '-U', '-r', requirements]) != 0:
                    print constants.TerminalColor.error(
                        'Failed to install requirements for %s.' % pluginName
                    )
    finally:
        shutil.rmtree(tmp)
    return found

__all__ = ('install_plugin', 'install_web')
