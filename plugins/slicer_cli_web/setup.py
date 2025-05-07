import os
import re

from setuptools import find_packages, setup


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

# perform the install
setup(
    name='girder-slicer-cli-web',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme},
    setup_requires=[
        'setuptools-scm',
        'setuptools-git',
    ],
    description='A girder plugin for exposing slicer CLIs over the web',
    long_description=readme,
    long_description_content_type='text/x-rst',
    url='https://github.com/girder/slicer_cli_web',
    keywords='girder-plugin, slicer_cli_web',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache Software License 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    include_package_data=True,
    packages=find_packages(exclude=['tests', 'test.*']),
    zip_safe=False,
    install_requires=[
        'girder>=5.0.0a2',
        'girder-jobs>=5.0.0a2',
        'girder-worker>=5.0.0a4',
        'girder-client',
        'ctk_cli',
        'jinja2',
        'jsonschema',
        'pyyaml',
    ],
    extras_require={
        'girder': [],  # preserved for backward compatibility
        'worker': [
            'docker>=2.6.0',
        ],
        'client': [
            'click',
        ]
    },
    entry_points={
        'girder.plugin': [
            'slicer_cli_web = slicer_cli_web.girder_plugin:SlicerCLIWebPlugin'
        ],
        'girder_worker_plugins': [
            'slicer_cli_web = slicer_cli_web.girder_worker_plugin:SlicerCLIWebWorkerPlugin'
        ],
        'console_scripts': [
            'upload-slicer-cli-task = slicer_cli_web.upload_slicer_cli_task:upload_slicer_cli_task'  # noqa: E501
        ]
    },
    python_requires='>=3.8',
)
