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
import itertools
import sys

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

installReqs = [
    'boto3>=1.7,<1.8',  # TODO: unpin once moto works with boto3>=1.8
    'botocore<1.11.0',  # TODO: remove once moto works with boto3>=1.8
    # CherryPy version is restricted due to a bug in versions >=11.1
    # https://github.com/cherrypy/cherrypy/issues/1662
    'CherryPy<11.1',
    'click',
    'click-plugins',
    'dogpile.cache',
    'filelock',
    'funcsigs ; python_version < \'3\'',
    'jsonschema',
    'Mako',
    'passlib [bcrypt,totp]',
    'pymongo>=3.5',
    'PyYAML',
    'psutil',
    'pyOpenSSL',
    'python-dateutil<2.7',  # required for compatibility with botocore=1.9.8
    'pytz',
    'requests',
    'shutilwhich ; python_version < \'3\'',
    'six>=1.9',
]

extrasReqs = {
    'authorized_upload': ['girder-authorized-upload'],
    'autojoin': ['girder-autojoin'],
    'curation': ['girder-curation'],
    'candela': ['girder-candela'],
    'dicom_viewer': ['girder-dicom-viewer'],
    'download_statistics': ['girder-download-statistics'],
    'google_analytics': ['girder-google-analytics'],
    'gravatar': ['girder-gravatar'],
    'hashsum_download': ['girder-hashsum-download'],
    'homepage': ['girder-homepage'],
    'item_licenses': ['girder-item-licenses'],
    'item_tasks': ['girder-item-tasks'],
    'jobs': ['girder-jobs'],
    'ldap': ['girder-ldap'],
    'oauth': ['girder-oauth'],
    'metadata_history': ['girder-metadata-history'],
    'table_view': ['girder-table-view'],
    'terms': ['girder-terms'],
    'thumbnails': ['girder-thumbnails'],
    'treeview': ['girder-treeview'],
    'quota': ['girder-user-quota'],
    'worker': ['girder-worker'],
    'virtual_folders': ['girder-virtual-folders']
}
if sys.version_info[0] < 3:
    extrasReqs['hdfs_assetstore'] = ['girder-hdfs-assetstore']

extrasReqs['plugins'] = list(set(itertools.chain.from_iterable(extrasReqs.values())))
extrasReqs['sftp'] = [
    'paramiko',
]
extrasReqs['mount'] = [
    'fusepy>=2.0.4,<3.0',
]

init = os.path.join(os.path.dirname(__file__), 'girder', '__init__.py')
with open(init) as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(), re.MULTILINE).group(1)

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
    include_package_data=True,
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    install_requires=installReqs,
    extras_require=extrasReqs,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'girder-server = girder.cli.serve:main',
            'girder-sftpd = girder.cli.sftpd:main',
            'girder-shell = girder.cli.shell:main',
            'girder = girder.cli:main'
        ],
        'girder.cli_plugins': [
            'serve = girder.cli.serve:main',
            'mount = girder.cli.mount:main',
            'shell = girder.cli.shell:main',
            'sftpd = girder.cli.sftpd:main',
            'build = girder.cli.build:main'
        ]
    }
)
