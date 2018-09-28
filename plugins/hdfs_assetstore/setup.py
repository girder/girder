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

description = (
    'This plugin adds a new assetstore type to the system that proxies files for '
    'the Hadoop Distributed Filesystem (HDFS). This also allows files on a '
    'pre-existing HDFS instance to be imported into the Girder data hierarchy.'
)

# perform the install
setup(
    name='girder-hdfs-assetstore',
    version='2.0.0a1',
    description=description,
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='http://girder.readthedocs.io/en/latest/plugins.html#hdfs-assetstore',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7'
    ],
    include_package_data=True,
    packages=find_packages(exclude=['plugin_tests']),
    python_requires='<3.0',
    zip_safe=False,
    install_requires=['girder>=3.0.0a1', 'snakebite'],
    entry_points={
        'girder.plugin': [
            'hdfs_assetstore = girder_hdfs_assetstore:HDFSAssetstorePlugin'
        ]
    }
)
