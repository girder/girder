from setuptools import find_packages, setup

setup(
    name='slicer-cli-web-singularity',
    version='0.0.0',
    description='A girder plugin adding singularity support to slicer-cli-web',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache Software License 2.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    install_requires=['girder-slicer-cli-web', 'girder-worker-singularity'],
    entry_points={
        'girder_worker_plugins': [
            'slicer_cli_web_singularity = slicer_cli_web_singularity:SlicerCLISingularityWebWorkerPlugin',
        ]
    },
    packages=find_packages(),
    zip_safe=False
)
