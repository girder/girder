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
import os
import shutil
import sys

from setuptools import setup, find_packages
from setuptools.command.install import install
from distutils.dir_util import copy_tree
from pkg_resources import parse_requirements


class InstallWithOptions(install):
    def mergeDir(self, path, dest):
        """
        We don't want to delete the old dir, since it might contain third
        party plugin content from previous installations; we simply want to
        merge the existing directory with the new one.
        """
        copy_tree(path, os.path.join(dest, path))

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
        self.mergeDir('clients', dest)
        self.mergeDir('grunt_tasks', dest)
        self.mergeDir('plugins', dest)

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
        'Programming Language :: Python'
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
    cmdclass={
        'install': InstallWithOptions
    },
    entry_points={
        'console_scripts': [
            'girder-server = girder.__main__:main',
            'girder-install = girder.utility.install:main'
        ]
    }
)
