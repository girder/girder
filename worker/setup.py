import os
import re
import shutil
import setuptools

from setuptools.command.install import install


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


class CustomInstall(install):
    """
    Override the default install to add some custom install-time behavior.
    Namely, we create the local config file.
    """

    def run(self, *args, **kwargs):
        install.run(self, *args, **kwargs)

        distcfg = os.path.join('girder_worker', 'worker.dist.cfg')
        localcfg = os.path.join('girder_worker', 'worker.local.cfg')
        if not os.path.isfile(localcfg):
            print('Creating worker.local.cfg')
            shutil.copyfile(distcfg, localcfg)


with open('requirements.in') as f:
    install_reqs = f.readlines()

setuptools.setup(
    name='girder-worker',
    use_scm_version={'root': '..', 'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools_scm', 'setuptools-git'],
    description='Batch execution engine built on celery.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='https://github.com/girder/girder_worker',
    license='Apache 2.0',
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
    packages=setuptools.find_packages(
        exclude=('tests.*', 'tests')
    ),
    include_package_data=True,
    cmdclass={
        'install': CustomInstall
    },
    install_requires=install_reqs,
    python_requires='>=3.8',
    zip_safe=False,
    entry_points={
        'girder_worker_plugins': [
            'docker = girder_worker.docker:DockerPlugin [docker]'
        ],
        'girder_worker._test_plugins.valid_plugins': [
            'plugin1 = girder_worker._test_plugins.plugins:TestPlugin1',
            'plugin2 = girder_worker._test_plugins.plugins:TestPlugin2'
        ],
        'girder_worker._test_plugins.invalid_plugins': [
            'exception1 = girder_worker._test_plugins.plugins:TestPluginException1',  # noqa
            'exception2 = girder_worker._test_plugins.plugins:TestPluginException2',  # noqa
            'import = girder_worker._test_plugins.plugins:TestPluginInvalidModule',  # noqa
            'invalid = girder_worker._test_plugins.plugins:NotAValidClass'
        ],
    }
)
