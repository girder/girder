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

from setuptools import setup, find_packages


# perform the install
setup(
    name='girder-plugin-candela',
    version='0.2.0',
    description='Render Candela visualizations in the item page for CSV files.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='http://girder.readthedocs.io/en/latest/plugins.html#candela-visualization',
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
    package_data={
        '': ['web_client/**']
    },
    packages=find_packages(exclude=['plugin_tests']),
    install_requires=['girder'],
    entry_points={
        'girder.plugin': [
            'candela = girder_plugin_candela:CandelaPlugin'
        ]
    }
)
