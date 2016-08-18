import os
from setuptools import setup

setupPath = os.path.dirname(os.path.realpath(__file__))
os.chdir(setupPath)

setup(
    name='entry_point_json_plugin',
    py_modules=['entry_point_json_plugin'],
    entry_points={
        'girder.plugin':
            'entry_point_json_plugin = entry_point_json_plugin:load'
    },
    data_files=[
        ('girder', ['plugin.json']),
    ],
    include_package_data=True,
    zip_safe=True,
)
