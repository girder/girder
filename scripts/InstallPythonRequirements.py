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

from __future__ import print_function

import argparse
import os
import subprocess
import sys


def installReqs(file, pip):
    if not os.path.exists(file):
        return

    print('\033[32m*** Installing: %s\033[0m' % file)
    if subprocess.call([pip, 'install', '-U', '-r', file]) != 0:
        print('\033[1;91m*** Error installing %s, stopping.\033[0m' % file,
              file=sys.stderr)
        sys.exit(1)


def installFromDir(path, dev, pip):
    installReqs(os.path.join(path, 'requirements.txt'), pip)

    if dev:
        installReqs(os.path.join(path, 'requirements-dev.txt'), pip)


def main(args):
    basePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(basePath)
    isDevMode = args.mode in ('dev', 'devel', 'development')
    ignoredPlugins = [i.strip() for i in args.ignore_plugins.split(',') if i]

    installFromDir(basePath, isDevMode, args.pip)

    pluginsDir = os.path.join(basePath, 'plugins')
    for path in os.listdir(pluginsDir):
        if path in ignoredPlugins:
            print('\033[35m*** Skipping plugin: %s\033[0m' % path)
            continue

        pluginPath = os.path.join(pluginsDir, path)
        if os.path.isdir(pluginPath):
            installFromDir(pluginPath, isDevMode, args.pip)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Install all required pip packages.')
    parser.add_argument('-m', '--mode', default='prod',
                        help='install for "dev" or "prod" (the default)')
    parser.add_argument('-p', '--pip', default='pip',
                        help='alternate path to pip executable')
    parser.add_argument('-i', '--ignore-plugins', help='skip install for a '
                        'set of plugins (comma separated)', default='')
    args = parser.parse_args()

    print(
        '\033[33;7m⚠⚠⚠ WARNING: This script is depreciated '
        'and will be removed in the future. ⚠⚠⚠\033[0m',
        file=sys.stderr
    )
    main(args)
