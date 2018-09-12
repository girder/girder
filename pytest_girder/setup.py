from setuptools import find_packages, setup

setup(
    name='pytest-girder',
    version='0.0.1',
    description='A set of pytest fixtures for testing Girder applications.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache 2.0',
    classifiers=[
        'Framework :: Pytest'
    ],
    packages=find_packages(),
    install_requires=[
        'girder',
        'mongomock',
        'pytest>=3.6',
        'pytest-cov<2.6',
        'pymongo'
    ],
    entry_points={
        'pytest11': [
            'girder = pytest_girder.plugin'
        ]
    })
