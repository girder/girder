=============
Release Notes
=============

This is the summary list of changes to Girder between each release. For full
details, see the commit logs at https://github.com/girder/girder

Unreleased
==========

Added Features
--------------

Bug fixes
---------

Security Fixes
--------------

Changes
-------

Web Client
^^^^^^^^^^
* Use ``href`` properties for navigation links in place of JavaScript onclick events. (`#2489 <https://github.com/girder/girder/pull/2489>`_)

Deprecations
------------

Removals
--------

Girder 2.4.0
============

Added Features
--------------
Server
^^^^^^
* Support for S3 buckets in regions other than us-east-1. (`#2153 <https://github.com/girder/girder/pull/2153>`_)
* Allow S3 credentials to be inferred by Boto. (`#2229 <https://github.com/girder/girder/pull/2229>`_)
* ``girder-shell`` console script which drops the user into a python repl with a configured webroot, giving the user the ability to import from any of the plugins specified. (`#2141 <https://github.com/girder/girder/pull/2141>`_)
* Support for configuration of pymongo client options as Girder config file options. (`#2380 <https://github.com/girder/girder/pull/2380>`_)
* Support for idiomatic use of Girder's model classes. Rather than using ``ModelImporter.model`` with strings for the model and plugin names, you can now use python imports of the model classes and instantiate and use them directly. (`#2376 <https://github.com/girder/girder/pull/2376>`_)
* Support for mounting REST endpoints under a prefix. Useful for grouping related endpoints, such as those exposed by a plugin. (`#2395 <https://github.com/girder/girder/pull/2395>`_)
* Option in worker task input specs to use local file paths in the worker when available, to avoid downloading files. (`#2356 <https://github.com/girder/girder/pull/2356>`_)
* Core setting allowing the instance brand name to be set. (`#2283 <https://github.com/girder/girder/pull/2283>`_)
* Core setting allowing the instance contact email address to be set. (`#2279 <https://github.com/girder/girder/pull/2279>`_)
* Core setting allowing the GUI header color to be set. (`#2334 <https://github.com/girder/girder/pull/2334>`_)
* “terms” plugin, which provides the option to require users to agree to a “Terms of Use” before accessing a collection. (`#2138 <https://github.com/girder/girder/pull/2138>`_)
* Improve the “homepage” plugin’s capabilities for making in-place changes to the home page. (`#2328 <https://github.com/girder/girder/pull/2328>`_)
* API endpoint, “/user/details”, allowing site admins to list the total number of users. (`#2262 <https://github.com/girder/girder/pull/2262>`_)
* Job cancellation support to Girder Worker jobs. (`#1983 <https://github.com/girder/girder/pull/1983>`_)
* Accept metadata on item and folder creation via the REST API. (`#2259 <https://github.com/girder/girder/pull/2259>`_)
* Allow ``girder-install plugin`` to get dependencies from a ``setup.py`` file. (`#2370 <https://github.com/girder/girder/pull/2370>`_)
* Create a registry for adding new search modes. (`#2363 <https://github.com/girder/girder/pull/2363>`_)

Web Client
^^^^^^^^^^
*  Published the Girder client side code as an npm package (https://www.npmjs.com/package/girder). (`#2242 <https://github.com/girder/girder/pull/2242>`_)

Python Client
^^^^^^^^^^^^^
* Support for turning off certificate checking with ``--no-ssl-verify``. (`#2433 <https://github.com/girder/girder/pull/2433>`_)
* Support for specifying a custom certificate with ``--certificate``. (`#2267 <https://github.com/girder/girder/pull/2267>`_)
* Support for downloading individual files. (`#2429 <https://github.com/girder/girder/pull/2429>`_)

DevOps
^^^^^^
* Added a Terraform module for creating an S3 bucket compliant with Girder assetstore policies. (`#2267 <https://github.com/girder/girder/pull/2267>`_)
* Published a latest-py3 tag to Dockerhub for Girder images built with Python 3. (`#2321 <https://github.com/girder/girder/pull/2321>`_)

Deprecations
------------
Python Client
^^^^^^^^^^^^^
* ``requests.HTTPError`` should be caught in places where ``girder_client.HttpError`` used to. (`#2223 <https://github.com/girder/girder/pull/2223>`_)

Bug fixes
---------
Server
^^^^^^
* Fixed an error where certain filenames could cause broken Content-Disposition header values. (`#2330 <https://github.com/girder/girder/pull/2330>`_)
* AccessControlledModel.load ``fields`` argument now works more reliably. (`#2366 <https://github.com/girder/girder/pull/2366>`_, `#2352 <https://github.com/girder/girder/pull/2352>`_)
* Fixed an issue where the events daemon was failing to terminate correctly. (`#2379 <https://github.com/girder/girder/pull/2379>`_)

Web Client
^^^^^^^^^^
* Remove Bootstrap re-styling of tooltips. (`#2406 <https://github.com/girder/girder/pull/2406>`_)

DevOps
^^^^^^
* Fixed an issue which disallowed provisioning with the Girder Ansible module under Python 3. (`#2449 <https://github.com/girder/girder/pull/2449>`_)

Girder 2.3.0
============

Bug fixes
---------

* Fix uploading into HDFS assetstore using new upload mode

Security Fixes
--------------

* Ensure token scopes on API keys are valid
* Add secure cookie setting
* Upgrade swagger-ui version to fix XSS issues

Added Features
--------------

* Add REST endpoint for creating job models
* Add graphs for Jobs status history to Admin UI
* Improvements to item_tasks job execution, task import, task lists, and permission flag UIs
* Show plugin load failures on plugins page
* Add Candela plugin
* Compute missing hashes when files are uploaded, and allow for hashsum calculation for non-filesystem assetstore files
* Add support for running Girder in AWS Elastic Beanstalk
* Upgrade S3 assetstore to Boto3
* Add LDAP authentication plugin
* Send all http server errors to the error log
* Added an event when the web client connection to the server is stopped or started
* Support uploading small files in a single REST call
* Improved GridFS support, including better sharding support and faster writes
* Add a Description method to mark a route as deprecated
* Many improvements to the web client test infrastructure including

  * A new CMake macro, `add_standard_plugin_tests`, to enable basic tests for a typical plugin layout
  * A new `girderTest.importPlugin` function, to load plugin JS and CSS in web client tests
  * A static analysis test for Stylus files
  * New rules for Javascript and Pug static analysis tests

* A facility to initialize the database to a specific state for testing

Changes
-------

* Upgrade web client to use jQuery 3
* Upgrade web client to use Backbone 1.3
* Require Node.js 6.5+ and npm 3.10+ (with npm 5.3 strongly recommended) to build the web client

Deprecations
------------

* job Plugin: Python Job model `listAll` method
* hashsum_download plugin: Python `HashedFile.supportedAlgorithms` symbol
* item_tasks plugin: `item_task_json_description` and `item_task_json_specs` routes
* `module.loaders` in webpack helper files, and the use of Webpack 1.0 syntax in plugins' webpack helper files
* `restRequest.error` in rest.js
* `npm-install` in client side build
* `girderTest.addCoveredScript` and `girderTest.addCoveredScripts` in testUtilities.js
* access to file paths outside `/static/built/` in the web client test environment

Removals
--------

* Remove the unmaintained external web client
