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


setup(
    name='pytest-girder',
    use_scm_version={'root': '..', 'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm'],
    description='A set of pytest fixtures for testing Girder applications.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache 2.0',
    classifiers=[
        'Framework :: Pytest'
    ],
    packages=find_packages(),
    install_requires=[
        'girder>=3.0.0a1',
        'mock',
        'mongomock',
        'pytest>=3.6',
        'pytest-cov',
        'pymongo'
    ],
    entry_points={
        'pytest11': [
            'girder = pytest_girder.plugin'
        ]
    })
