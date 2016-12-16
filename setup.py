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
import sys
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
        self.mergeDir('scripts', dest)

with open('README.rst') as f:
    readme = f.read()

install_reqs = [
    'bcrypt',
    'boto',
    'CherryPy<8',  # see https://github.com/girder/girder/issues/1615
    'Mako',
    'pymongo>=3',
    'PyYAML',
    'requests',
    'psutil',
    'python-dateutil',
    'pytz',
    'six>=1.9'
]

extras_reqs = {
    'celery_jobs': ['celery'],
    'geospatial': ['geojson'],
    'thumbnails': ['Pillow', 'pydicom', 'numpy'],
    'worker': ['celery'],
    'oauth': ['pyjwt', 'cryptography']
}
all_extra_reqs = itertools.chain.from_iterable(extras_reqs.values())
extras_reqs['plugins'] = list(set(all_extra_reqs))

if sys.version_info[0] == 2:
    install_reqs.append('shutilwhich')
    extras_reqs.update({
        'hdfs_assetstore': ['snakebite'],
        'metadata_extractor': [
            'hachoir-core',
            'hachoir-metadata',
            'hachoir-parser'
        ],
        'plugins': extras_reqs['plugins'] + [
            'snakebite',
            'hachoir-core',
            'hachoir-metadata',
            'hachoir-parser'
        ]
    })

extras_reqs['sftp'] = ['paramiko']

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
        'Programming Language :: Python :: 3.4'
    ],
    packages=find_packages(
        exclude=('tests.*', 'tests', '*.plugin_tests.*', '*.plugin_tests')
    ),
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
    install_requires=install_reqs,
    extras_require=extras_reqs,
    zip_safe=False,
    cmdclass={
        'install': InstallWithOptions
    },
    entry_points={
        'console_scripts': [
            'girder-server = girder.__main__:main',
            'girder-install = girder.utility.install:main',
            'girder-sftpd = girder.api.sftp:_main'
        ]
    }
)
