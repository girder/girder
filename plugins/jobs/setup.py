from setuptools import setup


setup(
    name='girder-plugin-jobs',
    py_modules=['girder_plugin_jobs'],
    entry_points={
        'girder.plugin': 'jobs = girder_plugin_jobs:load'
    }
)
