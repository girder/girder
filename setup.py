import os
import re

from setuptools import setup


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.
    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    # this regex allows us to publish pypi packages from master, our LTS maintenance branches, and
    # our next major version integration branches
    pattern = r'master|[0-9]+\.x-maintenance|v[0-9]+-integration'

    if re.match(pattern, os.getenv('CIRCLE_BRANCH', '')):
        return ''
    else:
        return get_local_node_and_date(version)


with open('README.rst') as f:
    readme = f.read()

installReqs = [
    'boto3',
    'botocore',
    'CherryPy',
    'click',
    'click-plugins',
    'dogpile.cache<1.4',
    'filelock',
    'girder-worker>=5.0.0a5',
    'jsonschema',
    'Mako',
    'passlib [bcrypt,totp]',
    'pymongo>=4',
    'PyYAML',
    'psutil',
    'pyOpenSSL',
    'python-dateutil',
    'pytz',
    'requests',
]

extrasReqs = {
    'sftp': [
        'paramiko'
    ],
    'mount': [
        'cachetools',
        'diskcache',
        'fusepy>=3.0'
    ]
}

setup(
    name='girder',
    use_scm_version={'local_scheme': prerelease_local_scheme},
    setup_requires=[
        'setuptools-scm',
    ],
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
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3.8',
    packages=['girder'],
    include_package_data=True,
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
        ],
        'girder_worker_plugins': [
            'girder_local = girder.worker_plugin:CoreWorkerPlugin',
        ],
    }
)
