# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.
    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') == 'master':
        return ''
    else:
        return get_local_node_and_date(version)


install_reqs = [
    'click>=6.7',
    'diskcache',
    'requests>=2.4.2',
    'requests_toolbelt',
]
with open('README.rst') as f:
    readme = f.read()

# perform the install
setup(
    name='girder-client',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm'],
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
        'Programming Language :: Python :: 3'
    ],
    packages=find_packages(exclude=('tests.*', 'tests')),
    install_requires=install_reqs,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'girder-cli = girder_client.cli:main',
            'girder-client = girder_client.cli:main'
        ]
    }
)
