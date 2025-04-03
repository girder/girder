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


with open('README.md') as readme_file:
    readme = readme_file.read()


setup(
    name='girder-import-tracker',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme},
    setup_requires=[
        'setuptools-scm',
        'setuptools-git',
    ],
    description='A Girder plugin for data import tracking',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='https://github.com/girder/girder/tree/master/plugins/import_tracker',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    install_requires=[
        'girder-jobs>=3.0.3',
        'girder>=3.1.23',
    ],
    include_package_data=True,
    keywords='girder-plugin, import_tracker',
    packages=find_packages(exclude=['plugin_tests']),
    zip_safe=False,
    entry_points={
        'girder.plugin': [
            'import_tracker = girder_import_tracker:GirderPlugin'
        ]
    }
)
