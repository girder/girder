Javascript Testing
======


## Dependencies

[Jasmine Testing Framework](https://github.com/pivotal/jasmine) MIT license
[Blanket Code Coverage Library](https://github.com/alex-seville/blanket) MIT license


## Install

Before you test the javascript files, you need to have the whole system installed
and runnable.  See the main README [TODO link] for instructions.

You'll need to have phantomjs installed via npm.

## Run

run the main server as

    python -m girder test

Then you can see the tests in action:


    http://localhost:8080/test/TestRunner.html

You can also run this on the command line (phantomjs is in the npm .bin dir, you'll need to issue the path to it if this is not in your PATH)

phantomjs PATH_TO_GIRDER/clients/web/test/lib/blanket/phantom_jasmine_runner.js http://localhost:8080/test/TestRunner.html


## TODO

*integrate this with the jshint testing
*use grunt to automatically assemble the list of js files under test in the TestRunner.html
