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
    name='girder-plugin-item-tasks',
    version='0.2.0',
    description=('Allows items in Girder to be used as specifications for tasks to be '
                 'run on the worker.'),
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='http://girder.readthedocs.io/en/latest/plugins.html#item-tasks',
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
    install_requires=[
        'girder',
        'girder-plugin-jobs',
        'girder-plugin-worker',
        'ctk-cli',
        'girder-worker>=0.4.0',
        'girder-worker-utils>=0.7.2'
    ],
    entry_points={
        'girder.plugin': [
            'item_tasks = girder_plugin_item_tasks:ItemTasksPlugin'
        ]
    }
)
