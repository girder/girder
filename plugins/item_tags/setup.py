from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = [
    'girder>=3.0.0a1'
]

setup(
    author='Daniel Chiquito',
    author_email='daniel.chiquito@kitware.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    description='Searchable keyword tags for items.',
    install_requires=requirements,
    license='Apache Software License 2.0',
    long_description=readme,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='girder-plugin, item_tags',
    name='girder-item-tags',
    packages=find_packages(exclude=['test', 'test.*']),
    url='https://github.com/girder/girder',
    version='0.1.0',
    zip_safe=False,
    entry_points={
        'girder.plugin': [
            'item_tags = girder_item_tags:GirderPlugin'
        ]
    }
)
