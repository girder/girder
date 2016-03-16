from setuptools import setup


setup(
    name='girder-entry-point-plugin',
    py_modules=['entry_point_plugin'],
    entry_points={
        'girder.plugin': 'test_entry_point = entry_point_plugin:load'
    }
)
