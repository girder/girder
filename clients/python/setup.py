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

import os
import sys

from setuptools import setup, find_packages
from setuptools.command.install import install
from pkg_resources import parse_requirements


CLIENT_VERSION = '0.1.0'

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = []
try:
    install_reqs = parse_requirements(open('requirements.txt').read())
except Exception:
    pass

# reqs is a list of requirement
reqs = [str(req) for req in install_reqs]

with open('README.rst') as f:
    readme = f.read()

# perform the install
setup(
    name='girder-client',
    version=CLIENT_VERSION,
    description='Python client for interacting with Girder servers',
    long_description=readme,
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='http://girder.readthedocs.org/en/latest/python-client.html',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2'
    ],
    packages=find_packages(exclude=('tests.*', 'tests')),
    install_requires=reqs,
    zip_safe=False,
    scripts=['girder-cli']
)
