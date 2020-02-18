# -*- coding: utf-8 -*-
import os

from setuptools import find_packages, setup


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


root = os.path.dirname(__file__) + '/../..'
setup(
    name='girder-thumbnails',
    use_scm_version={'root': root, 'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm', 'setuptools-git'],
    description='Generate thumbnails from files.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6'
    ],
    include_package_data=True,
    packages=find_packages(exclude=['plugin_tests']),
    zip_safe=False,
    install_requires=[
        'girder>=3',
        'girder-jobs>=3',
        'Pillow',
        'pydicom>=1.0.2',
        'numpy'
    ],
    entry_points={
        'girder.plugin': [
            'thumbnails = girder_thumbnails:ThumbnailsPlugin'
        ]
    }
)
