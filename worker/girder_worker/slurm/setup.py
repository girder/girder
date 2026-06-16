import os

from setuptools import find_packages, setup


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.

    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).

    """

    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') in ('master', ):
        return ''
    else:
        return get_local_node_and_date(version)


with open('requirements.txt') as f:
    install_reqs = f.readlines()

setup(
    name='girder-worker-slurm',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme,
                     'fallback_version': '0.0.0'},
    description='Enables Slurm support for Worker Singularity.',
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
    install_requires=['girder-worker', 'girder-worker-singularity', *install_reqs],
    entry_points={
        'girder.plugin': [
            'worker_slurm = girder_worker_slurm.girder_plugin:WorkerSlurmPlugin',
        ],
    },
    packages=find_packages(),
    zip_safe=False
)
