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
import re
from setuptools import setup, find_packages

install_reqs = [
    'diskcache',
    'requests>=2.4.2',
    'six'
]
with open('README.rst') as f:
    readme = f.read()

init = os.path.join(os.path.dirname(__file__), 'girder_client', '__init__.py')
with open(init) as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(), re.MULTILINE).group(1)

# perform the install
setup(
    name='girder-client',
    version=version,
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
    install_requires=install_reqs,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'girder-cli = girder_client.cli:main'
        ]
    }
)
