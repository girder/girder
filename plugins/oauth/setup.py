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


# perform the install
setup(
    name='girder-oauth',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme},
    setup_requires=[
        'setuptools-scm',
        'setuptools-git',
    ],
    description='Allow users to login via supported OAuth2 providers.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='http://girder.readthedocs.io/en/latest/plugins.html#oauth-login',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    include_package_data=True,
    python_requires='>=3.8',
    packages=find_packages(exclude=['plugin_tests']),
    zip_safe=False,
    install_requires=[
        'girder>=3',
        'msal',
        'pyjwt>=2,<3',
    ],
    entry_points={
        'girder.plugin': [
            'oauth = girder_oauth:OAuthPlugin'
        ]
    }
)
