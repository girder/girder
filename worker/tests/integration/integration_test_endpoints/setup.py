from setuptools import setup

setup(
    name='integration_test_endpoints',
    version='0.1.0',
    description='Girder endpoints for Girder Worker integration tests',
    author='Kitware Inc.',
    author_email='kitware@ktiware.com',
    url='',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License'
    ],
    packages=['integration_test_endpoints'],
    zip_safe=False,
    install_requires=['girder>=3', 'girder-jobs'],
    entry_points={
        'girder.plugin': [
            'integration_test_endpoints = integration_test_endpoints:IntegrationTestPlugin'
        ]
    }
)
