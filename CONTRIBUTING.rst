Contributing to Girder
======================

There are many ways to contribute to Girder, with varying levels of effort.  Do try to
look through the documentation first if something is unclear, and let us know how we can
do better.

- Ask a question on the `Girder users email list <http://public.kitware.com/mailman/listinfo/girder-users>`_
- Ask a question in the `Gitter Forum <https://gitter.im/girder/girder>`_
- Submit a feature request or bug, or add to the discussion on the `Girder issue tracker <https://github.com/girder/girder/issues>`_
- Submit a `Pull Request <https://github.com/girder/girder/pulls>`_ to improve Girder or its documentation

We encourage a range of contributions, from patches that include passing tests and
documentation, all the way down to half-baked ideas that launch discussions.

The PR Process, CircleCI, and Related Gotchas
---------------------------------------------

How to submit a PR
^^^^^^^^^^^^^^^^^^

If you are new to Girder development and you don't have push access to the Girder
repository, here are the steps:

1. `Fork and clone <https://help.github.com/articles/fork-a-repo/>`_ the repository.
2. Create a branch.
3. `Push <https://help.github.com/articles/pushing-to-a-remote/>`_ the branch to your GitHub fork.
4. Create a `Pull Request <https://github.com/girder/girder/pulls>`_.

This corresponds to the ``Fork & Pull Model`` mentioned in the
`GitHub flow <https://guides.github.com/introduction/flow/index.html>`_ guides.

If you have push access to Girder repository, you could simply push your branch
into the main repository and create a `Pull Request <https://github.com/girder/girder/pulls>`_. This
corresponds to the ``Shared Repository Model`` and will facilitate other developers to checkout your
topic without having to `configure a remote <https://help.github.com/articles/configuring-a-remote-for-a-fork/>`_.
It will also simplify the workflow when you are *co-developing* a branch.

When submitting a PR, make sure to add a ``Cc: @girder/developers`` comment to notify Girder
developers of your awesome contributions. Based on the
comments posted by the reviewers, you may have to revisit your patches.

Automatic testing of pull requests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you submit a PR to the Girder repo, CircleCI will run the build and test suite on the
head of the branch. If you add new commits onto the branch, those will also automatically
be run through the CI process. The status of the CI process (passing, failing, or in progress) will
be displayed directly in the PR page in GitHub.

The CircleCI build will run according to the `circle.yml file <https://github.com/girder/girder/blob/master/circle.yml>`_,
which is useful as an example for how to set up your own environment for testing.

Your test results will be posted on `Girder's CircleCI dashboard <https://circleci.com/gh/girder>`_.
These results will list any failed tests. Coverage reports and any screenshots
from failed web client tests will be attached to the build as artifact files. You can reach your
build by clicking the build status link on your GitHub PR.

Confusing failing test message "AttributeError: 'module' object has no attribute 'x_test'"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is also a gotcha for your local testing environment.  If a new dependency is
introduced during development, but is not in the test environment, usually because the
dependency is not included in a ``requirements.txt`` or ``requirements-dev.txt`` file, or
because those requirements are not installed via ``pip``, a test can fail that attempts to
import that dependency and can print a confusing message in the test logs like
"AttributeError: 'module' object has no attribute 'x_test'".

As an example, the HDFS plugin has a dependency on the Python module ``snakebite``, specified in the
`HDFS plugin requirements.txt file <https://github.com/girder/girder/blob/master/plugins/hdfs_assetstore/requirements.txt>`_.
If this dependency was not included in the requirements file, or if that requirements file
was not included in the `circle.yml file <https://github.com/girder/girder/blob/master/circle.yml>`_
(or that requirements file was not ``pip`` installed in a local test environment), when the test defined in
`the assetstore_test.py file <https://github.com/girder/girder/blob/master/plugins/hdfs_assetstore/plugin_tests/assetstore_test.py#L27-L28>`_
is run, the ``snakebite`` module will not be found, but the exception will be swallowed by
the testing environment and instead the ``assetstore_test`` module will be considered
invalid, resulting in the confusing error message::

    AttributeError: 'module' object has no attribute 'assetstore_test'

but you won't be confused now, will you?

How to integrate a PR
^^^^^^^^^^^^^^^^^^^^^

Getting your contributions integrated is relatively straightforward, here is the checklist:

- All tests pass
- Any significant changes are added to the ``CHANGELOG.rst`` with human-readable and understandable
  text (i.e. not a commit message). Text should be placed in the "Unreleased" section, and grouped
  into the appropriate sub-section of:

  - Bug fixes
  - Security fixes
  - Added features
  - Changes
  - Deprecations
  - Removals

- Consensus is reached. This requires that a reviewer adds an "approved" review via GitHub with no
  changes requested, and a reasonable amount of time passed without anyone objecting.

Next, there are two scenarios:

- You do NOT have push access: A Girder core developer will integrate your PR.
- You have push access: Simply click on the "Merge pull request" button.

Then, click on the "Delete branch" button that appears afterward.
