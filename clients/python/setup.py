import os

from setuptools import setup


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.
    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') == 'master':
        return ''
    else:
        return get_local_node_and_date(version)


# perform the install
setup(
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme},
)
