# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

# perform the install
setup(
    name='girder-sentry',
    setup_requires=['setuptools-scm', 'setuptools-git'],
    description='Allow the automatic tracking of issues using Sentry.',
    maintainer='Kitware, Inc.',
    maintainer_email='kitware@kitware.com',
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
        'Programming Language :: Python :: 3.5'
    ],
    include_package_data=True,
    packages=find_packages(exclude=['plugin_tests']),
    zip_safe=False,
    install_requires=['girder>=3.0.0a1'],
    entry_points={
        'girder.plugin': [
            'sentry = girder_sentry:SentryPlugin'
        ]
    }
)
