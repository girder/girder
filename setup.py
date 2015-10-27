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

import json
import sys

from setuptools import setup, find_packages
from setuptools.command.install import install
from pkg_resources import parse_requirements


class InstallWithOptions(install):
    """
    A custom install command that recognizes extra options
    to perform plugin and/or web client installation.
    """

    user_options = install.user_options + [
        ('plugins', None, 'Install default plugins.'),
        ('web', None, 'Install web client resources.')
    ]

    boolean_options = install.boolean_options + [
        'plugins', 'web'
    ]

    def initialize_options(self, *arg, **kw):
        install.initialize_options(self, *arg, **kw)
        self.plugins = None
        self.web = None

    def run(self, *arg, **kw):
        """
        Runs the main installation, then installs optional
        components.  This will fail if (for whatever reason)
        the installation path is not in ``sys.path``.
        """
        install.run(self, *arg, **kw)
        if self.plugins:
            print('Installing plugins')
            self.girder_install('plugins')
        if self.web:
            print('Installing web components')
            self.girder_install('web')

    def girder_install(self, component):
        """
        Try to import girder_install to install
        optional components.
        """
        try:
            from girder.utility import install
        except ImportError:
            sys.stderr.write(
                'Install {} failed.  '.format(component) +
                'Could not import girder.\n'
            )
            return
        if component == 'web':
            install.install_web(force=True)
        elif component == 'plugins':
            install.install_plugin(force=True)

with open('README.rst') as f:
    readme = f.read()

with open('package.json') as f:
    version = json.load(f)['version']

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = []
try:
    install_reqs = parse_requirements(open('requirements.txt').read())
except Exception:
    pass

# reqs is a list of requirement
reqs = [str(req) for req in install_reqs]

# perform the install
setup(
    name='girder',
    version=version,
    description='High-performance data management platform',
    long_description=readme,
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='https://girder.readthedocs.org',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2'
    ],
    packages=find_packages(exclude=('tests.*', 'tests')),
    package_data={
        'girder': [
            'girder-version.json',
            'conf/girder.dist.cfg',
            'mail_templates/*.mako',
            'mail_templates/**/*.mako',
            'utility/webroot.mako',
            'api/api_docs.mako'
        ]
    },
    install_requires=reqs,
    zip_safe=False,
    scripts=['girder-install'],
    cmdclass={
        'install': InstallWithOptions
    },
    entry_points={
        'console_scripts': [
            'girder-server = girder.__main__:main'
        ]
    }
)
