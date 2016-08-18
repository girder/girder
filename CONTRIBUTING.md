Contributing to Girder
======================

There are many ways to contribute to Girder, with varying levels of effort.  Do try to
look through the documentation first if something is unclear, and let us know how we can
do better.

  * Ask a question on the [Girder users email list](http://public.kitware.com/mailman/listinfo/girder-users)
  * Ask a question in the [Gitter Forum](https://gitter.im/girder/girder)
  * Submit a feature request or bug, or add to the discussion on the [Girder issue tracker](https://github.com/girder/girder/issues)
  * Submit a [Pull Request](https://github.com/girder/girder/pulls) to improve Girder or its documentation

We encourage a range of Pull Requests, from patches that include passing tests and
documentation, all the way down to half-baked ideas that launch discussions.

The PR Process, Travis CI, and Related Gotchas
----------------------------------------------

#### How to submit a PR ?

If you are new to Girder development and you don't have push access to the Girder
repository, here are the steps:

1. [Fork and clone](https://help.github.com/articles/fork-a-repo/) the repository.
3. Create a branch.
4. [Push](https://help.github.com/articles/pushing-to-a-remote/) the branch to your GitHub fork.
5. Create a [Pull Request](https://github.com/girder/girder/pulls).

This corresponds to the `Fork & Pull Model` mentioned in the [GitHub flow](https://guides.github.com/introduction/flow/index.html)
guides.

If you have push access to Girder repository, you could simply push your branch
into the main repository and create a [Pull Request](https://github.com/girder/girder/pulls). This corresponds to the
`Shared Repository Model` and will facilitate other developers to checkout your
topic without having to [configure a remote](https://help.github.com/articles/configuring-a-remote-for-a-fork/).
It will also simplify the workflow when you are _co-developing_ a branch.

When submitting a PR, make sure to add a `Cc: @girder/developers` comment to notify Girder
developers of your awesome contributions. Based on the
comments posted by the reviewers, you may have to revisit your patches.

### How to integrate a PR ?

Getting your contributions integrated is relatively straightforward, here
is the checklist:

* All tests pass
* Consensus is reached. This usually means that at least one reviewer added a `LGTM` comment
and a reasonable amount of time passed without anyone objecting. `LGTM` is an
acronym for _Looks Good to Me_.

Next, there are two scenarios:
* You do NOT have push access: A Girder core developer will integrate your PR.
* You have push access: Simply click on the "Merge pull request" button.

Then, click on the "Delete branch" button that appears afterward.

#### Automatic testing of pull requests

When you submit a PR to the Girder repo, Travis CI will run the full build on two different branches

  * The commit at the head of the PR branch, the `push` build
  * The head of the PR branch that is then merged into `master`, the `pr` branch

The Travis build will run according to the [.travis.yml file](/.travis.yml), which is
useful as an example for how to set up your own environment for testing.  We are currently
using containerized builds on Travis, and for each branch, will test against both Mongo
v2.6.8 and Mongo v3.0.1.

The tests that run in Travis are harnessed with CTest, which submits the results of its
automated testing to [Girder's CDash dashboard](http://my.cdash.org/index.php?project=girder)
where the test and coverage results can be easily visualized and explored.

#### Confusing failing test message "AttributeError: 'module' object has no attribute 'x_test'"

This is also a gotcha for your local testing environment.  If a new dependency is
introduced during development, but is not in the test environment, usually because the
dependency is not included in a `requirements.txt` or `requirements-dev.txt` file, or
because those requirements are not installed via `pip`, a test can fail that attempts to
import that dependency and can print a confusing message in the test logs like
"AttributeError: 'module' object has no attribute 'x_test'".

As an example, the HDFS plugin has a dependency on the Python module `snakebite`,
specified in the
[HDFS plugin requirements.txt file](https://github.com/girder/girder/blob/master/plugins/hdfs_assetstore/requirements.txt).
If this dependency was not included in the requirements file, or if that requirements file
was not included in the [.travis.yml file](/.travis.yml) (or that requirements file was
not `pip` installed in a local test environment), when the test defined in
[the assetstore_test.py file](https://github.com/girder/girder/blob/master/plugins/hdfs_assetstore/plugin_tests/assetstore_test.py#L27-L28)
is run, the `snakebite` module will not be found, but the exception will be swallowed by
the testing environment and instead the `assetstore_test` module will be considered
invalid, resulting in the confusing error message

    AttributeError: 'module' object has no attribute 'assetstore_test'

but you won't be confused now, will you?
