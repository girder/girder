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

import os
import re
import shutil
import itertools

from setuptools import setup, find_packages
from setuptools.command.install import install
from distutils.dir_util import copy_tree


class InstallWithOptions(install):
    def mergeDir(self, path, dest):
        """
        We don't want to delete the old dir, since it might contain third
        party plugin content from previous installations; we simply want to
        merge the existing directory with the new one.
        """
        copy_tree(path, os.path.join(dest, path), preserve_symlinks=True)

    def run(self, *arg, **kw):
        """
        We override the default install command in order to copy our required
        package data underneath the package directory; in the egg, it is
        adjacent to the package dir.
        """
        install.run(self, *arg, **kw)

        dest = os.path.join(self.install_lib, 'girder')
        shutil.copy('Gruntfile.js', dest)
        shutil.copy('package.json', dest)
        self.mergeDir(os.path.join('clients', 'web', 'src'), dest)
        self.mergeDir(os.path.join('clients', 'web', 'static'), dest)
        shutil.copy(os.path.join('clients', 'web', 'src', 'assets', 'fontello.config.json'),
                    os.path.join(dest, 'clients', 'web', 'src', 'assets'))
        self.mergeDir('grunt_tasks', dest)
        self.mergeDir('plugins', dest)


with open('README.rst') as f:
    readme = f.read()

installReqs = [
    'bcrypt',
    'boto3',
    # CherryPy version is restricted due to a bug in versions >=11.1
    # https://github.com/cherrypy/cherrypy/issues/1662
    'CherryPy<11.1',
    'click',
    'dogpile.cache',
    'filelock',
    'funcsigs ; python_version < \'3\'',
    'jsonschema',
    'Mako',
    'pymongo>=3.5',
    'PyYAML',
    'psutil',
    'python-dateutil',
    'pytz',
    'requests',
    'shutilwhich ; python_version < \'3\'',
    'six>=1.9',
]

extrasReqs = {}
# To avoid conflict with the `girder-install plugin' command, this only adds built-in plugins with
# extras requirements.
# Note: the usage of automatically-parsed plugin-specific 'requirements.txt' is a temporary
# measure to keep plugin requirements close to plugin code. It will be removed when pip-installable
# plugins are added. It should not be used by other projects.
with open(os.path.join('plugins', '.gitignore')) as builtinPluginsIgnoreStream:
    builtinPlugins = set()
    for line in builtinPluginsIgnoreStream:
        # Plugin .gitignore entries should end with a /, but we will tolerate those that don't;
        # (accordingly, note the non-greedy qualifier for the match group)
        builtinPluginNameRe = re.match(r'^!(.+?)/?$', line)
        if builtinPluginNameRe:
            builtinPluginName = builtinPluginNameRe.group(1)
            if os.path.isdir(os.path.join('plugins', builtinPluginName)):
                builtinPlugins.add(builtinPluginName)
for pluginName in os.listdir('plugins'):
    pluginReqsFile = os.path.join('plugins', pluginName, 'requirements.txt')
    if pluginName in builtinPlugins and os.path.isfile(pluginReqsFile):
        with open(pluginReqsFile) as pluginReqsStream:
            pluginExtrasReqs = []
            for line in pluginReqsStream:
                line = line.strip()
                if line and not line.startswith('#'):
                    pluginExtrasReqs.append(line)
            extrasReqs[pluginName] = pluginExtrasReqs

extrasReqs['plugins'] = list(set(itertools.chain.from_iterable(extrasReqs.values())))
extrasReqs['sftp'] = [
    'paramiko',
]


init = os.path.join(os.path.dirname(__file__), 'girder', '__init__.py')
with open(init) as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(), re.MULTILINE).group(1)

# perform the install
setup(
    name='girder',
    version=version,
    description='Web-based data management platform',
    long_description=readme,
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='https://girder.readthedocs.org',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5'
    ],
    packages=find_packages(
        exclude=('girder.test', 'tests.*', 'tests', '*.plugin_tests.*', '*.plugin_tests')
    ),
    package_data={
        'girder': [
            'girder-version.json',
            'conf/girder.dist.cfg',
            'mail_templates/*.mako',
            'mail_templates/**/*.mako',
            'utility/*.mako',
            'api/api_docs.mako'
        ]
    },
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    install_requires=installReqs,
    extras_require=extrasReqs,
    zip_safe=False,
    cmdclass={
        'install': InstallWithOptions
    },
    entry_points={
        'console_scripts': [
            'girder-server = girder.__main__:main',
            'girder-install = girder.utility.install:main',
            'girder-sftpd = girder.api.sftp:_main',
            'girder-shell = girder.utility.shell:main'
        ]
    }
)
