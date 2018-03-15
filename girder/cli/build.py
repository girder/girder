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

import json
import os
from subprocess import check_call

import click

from girder.constants import STATIC_PREFIX, STATIC_ROOT_DIR
from girder.plugin import allPlugins, getPlugin

_GIRDER_STAGING_MARKER = '.girder-staging'

# TODO: add build assets to an npm package (or the python package)
# For the moment, the static assets are in the repository root for
# development installs and in `site-packages/girder/` for regular
# installs.  There is no direct way to detect which environment we
# are currently in.  For now, we just detect where the toplevel
# Gruntfile.js is and use that as the root path.  In the future,
# we may want to move these into the python package and specify it
# as package_data, avoiding the custom setup.py install step entirely.
_GIRDER_BUILD_ASSETS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..'))
if os.path.exists(os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'girder', 'Gruntfile.js')):
    _GIRDER_BUILD_ASSETS_PATH = os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'girder')
elif not os.path.exists(os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'Gruntfile.js')):
    raise Exception('Could not find girder client build assets')


@click.command(name='build', help='Build web client static assets.')
@click.option('--staging', type=click.Path(file_okay=False, writable=True, resolve_path=True),
              default=os.path.join(STATIC_PREFIX, 'staging'),
              help='Path to a staging area.')
@click.option('--dev/--no-dev', default=False,
              help='Build girder client for development.')
def main(staging, dev):
    _generateStagingArea(staging, dev)

    # The autogeneration of package.json breaks how package-lock.json is
    # intended to work.  If we don't delete it first, you will frequently
    # get "file doesn't exist" errors.
    npmLockFile = os.path.join(staging, 'package-lock.json')
    if os.path.exists(npmLockFile):
        os.unlink(npmLockFile)

    check_call(['npm', 'install'], cwd=staging)
    buildCommand = [
        'npx', '-n', '--preserve-symlinks', 'grunt', '--static-path=%s' % STATIC_ROOT_DIR]
    if dev:
        buildCommand.append('--env=dev')
    else:
        buildCommand.append('--env=prod')
    check_call(buildCommand, cwd=staging)


def _checkStagingPath(staging):
    try:
        os.makedirs(staging)
    except OSError:  # directory already exists
        pass
    listdir = os.listdir(staging)
    if listdir and _GIRDER_STAGING_MARKER not in listdir:
        raise Exception('Staging directory is not empty')

    with open(os.path.join(staging, _GIRDER_STAGING_MARKER), 'w') as f:
        f.write('')


def _linkTestFiles(staging):
    source = os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'clients', 'web', 'test')
    target = os.path.join(staging, 'test')
    if os.path.exists(target):
        os.unlink(target)
    os.symlink(source, target)


def _npmInstallGirderSourcePath():
    # TODO: This is a hack to make many of the cmake based runners, which run
    # from girder's source tree to include necessary development npm libraries.
    # In the future, we could either limit the number of dependencies are in the
    # top-level girder repo, or move things like eslint checking and web client
    # test running into the staging area.
    check_call(['npm', 'install'], cwd=_GIRDER_BUILD_ASSETS_PATH)


def _generateStagingArea(staging, dev):
    _checkStagingPath(staging)
    for baseName in ['grunt_tasks', 'Gruntfile.js']:
        target = os.path.join(staging, baseName)
        if os.path.exists(target) or os.path.islink(target):
            os.unlink(target)
        os.symlink(os.path.join(_GIRDER_BUILD_ASSETS_PATH, baseName), target)
    _generatePackageJSON(staging, os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'package.json'))

    # copy swagger page source (TODO: make this better so it doesn't depend on the source dir)
    source = os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'clients', 'web', 'static',
                          'girder-swagger.js')
    target = os.path.join(staging, 'girder-swagger.js')
    if os.path.exists(target):
        os.unlink(target)
    os.symlink(source, target)

    if dev:
        _npmInstallGirderSourcePath()
        _linkTestFiles(staging)


def _collectPluginDependencies():
    packages = {}
    for pluginName in allPlugins():
        plugin = getPlugin(pluginName)
        packages.update(plugin.npmPackages())
    return packages


def _generatePackageJSON(staging, source):
    # TODO: use a template string
    with open(source, 'r') as f:
        sourceJSON = json.load(f)
    deps = sourceJSON['dependencies']
    deps['girder'] = 'file:%s' % os.path.join(
        _GIRDER_BUILD_ASSETS_PATH, 'clients', 'web', 'src')
    plugins = _collectPluginDependencies()
    deps.update(plugins)
    sourceJSON['girder'] = {
        'plugins': list(plugins.keys())
    }
    with open(os.path.join(staging, 'package.json'), 'w') as f:
        json.dump(sourceJSON, f)
