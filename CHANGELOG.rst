=============
Release Notes
=============

This is the summary list of changes to Girder between each release. For full
details, see the commit logs at https://github.com/girder/girder

Unreleased
==========

Added Features
--------------

* Support S3 buckets in regions other than us-east-1
* Allow S3 credentials to be inferred by Boto
* Add a girder-shell console script which drops the user into a python repl with a configured webroot, giving the user the ability to import from any of the plugins specified

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
