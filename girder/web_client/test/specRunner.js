/**
 * This is the PhantomJS runtime script that invokes the Girder app in test
 * mode. The test mode page is built with grunt and lives at:
 * girder/web_client/static/built/testing/testEnv.html. It then executes a Jasmine spec within
 * the context of that test application, and afterwards runs our custom coverage
 * handler on the coverage data.
 */
/* eslint-disable node/no-deprecated-api */
/* globals phantom, WebPage, jasmine, girderTest */

var fs = require('fs');

var system = require('system');
require('event-source/global');

var args = phantom.args ? phantom.args : system.args.slice(1);

if (args && args.length < 2) {
    console.error('Usage: phantomjs phantom_jasmine_runner.js <page> <spec> [<covg_output> [<default jasmine timeout>]');
    console.error('  <page> is the path to the HTML page to load');
    console.error('  <spec> is the path to the Jasmine spec to run.');
    console.error('  <default Jasmine timeout> is in milliseconds.');
    console.error('  <spec options> is any special spec options, to disambiguate to output filenames.');
    phantom.exit(2);
}

var env = system.env;

var pageUrl = args[0];
var spec = args[1];
var page = new WebPage();

// Determine the test name to be used for output files
var specPathComponents = spec.split('/');
var pluginName =
    specPathComponents[specPathComponents.length - 2] === 'plugin_tests'
        ? specPathComponents[specPathComponents.length - 3]
        : 'core';
var specName = specPathComponents[specPathComponents.length - 1].replace(/\.js$/, '');
var specOptions = args[3];
var testName = pluginName + '_' + specName + (specOptions ? '_' + specOptions : '');

var coverageDir = 'build/test/coverage/web_temp';
fs.makeTree(coverageDir);
var coverageFile = coverageDir + '/coverage_' + testName + '.json';
if (fs.exists(coverageFile)) {
    fs.remove(coverageFile);
}
// write coverage results to a file
function reportCoverage() {
    var cov = page.evaluate(function () {
        return window.__coverage__;
    });
    cov = cov || {};
    fs.write(coverageFile, JSON.stringify(cov), 'w');
}

// Set decent viewport size for screenshots.
page.viewportSize = {
    width: 1024,
    height: 769
};

var artifactDir = 'build/test/artifacts';
fs.makeTree(artifactDir);
page.onConsoleMessage = function (msg) {
    if (msg.indexOf('__SCREENSHOT__') === 0) {
        var screenshotTime = msg.substring('__SCREENSHOT__'.length);
        var screenshotFile = artifactDir + '/screenshot_' + testName + '_' + screenshotTime + '.png';
        page.render(screenshotFile);
        console.log('Created screenshot: ' + screenshotFile);

        if (env['PHANTOMJS_OUTPUT_AJAX_TRACE'] === undefined ||
            env['PHANTOMJS_OUTPUT_AJAX_TRACE'] === 1 ||
            env['PHANTOMJS_OUTPUT_AJAX_TRACE'] === true) {
            console.log(page.evaluate(function () {
                var log = girderTest.ajaxLog(true);
                return 'XHR log (last ' + log.length + '):\n' + JSON.stringify(log, null, '  ');
            }));
        }
        return;
    } else if (msg === 'ConsoleReporter finished') {
        var success = this.page.evaluate(function () {
            return window.jasmine_phantom_reporter.status === 'success';
        });
        if (success) {
            reportCoverage();
        }
        phantom.exit(success ? 0 : 1);
    }
    console.log(msg);
};

page.onCallback = function (data) {
    /* Perform an action asked for in the web test and return a result.  An
     * action must be specified in the data object for this to do anything.
     * Available actions are:
     *   uploadFile: upload the file in data.path to the element determined
     * with the selector data.selector.  If no path or an invalid path is
     * specified, and data.size is present, create a temporary file with
     * data.size bytes and upload that.
     *   uploadCleanup: delete any temporary file that was created for uploads.
     * :param data: an object with an 'action', as listed above.
     * :returns: depends on the action.
     */
    var uploadTemp = fs.workingDirectory + fs.separator + 'phantom_temp';
    if (data.suffix) {
        uploadTemp += '_' + data.suffix;
    }
    uploadTemp += '.tmp';
    switch (data.action) {
        case 'fetchEmail':
            if (fs.exists(uploadTemp)) {
                return fs.read(uploadTemp);
            }
            break;
        case 'uploadFile':
            var path = data.path;
            if (!path && data.size !== undefined) {
                path = uploadTemp;
                fs.write(path, new Array(data.size + 1).join('-'), 'wb');
            }
            page.uploadFile(data.selector, path);
            return fs.read(path, {
                mode: 'rb'
            });
        case 'uploadCleanup':
            if (fs.exists(uploadTemp)) {
                fs.remove(uploadTemp);
            }
            break;
        case 'exit':
            // The "Testing Finished" string is magical and causes web_client_test.py not to retry
            if (data.errorMessage) {
                console.error(data.errorMessage);
            }
            console.log('Testing Finished with status=' + data.code);
            phantom.exit(data.code);
    }
};

page.onError = function (msg, trace) {
    var msgStack = ['ERROR: ' + msg];
    if (trace && trace.length) {
        msgStack.push('TRACE:');
        trace.forEach(function (t) {
            msgStack.push(' -> ' + t.file + ': ' + t.line +
                (t.function ? ' (in function "' + t.function + '")' : ''));
        });
    }
    console.error(msgStack.join('\n'));

    var screenshotFile = artifactDir + '/screenshot_' + testName + '_error.png';
    page.render(screenshotFile);
    console.log('Created error screenshot: ' + screenshotFile);
    phantom.exit(1);
};

page.onLoadFinished = function (status) {
    if (status !== 'success') {
        console.error('Page load failed');
        // Avoid Unsafe JavaScript attempt to access frame with URL
        // http://stackoverflow.com/a/26688062/250457
        setTimeout(function () {
            phantom.exit(1);
        }, 0);
    } else {
        if (!page.injectJs(spec)) {
            console.error('Could not load test spec into page: ' + spec);
            phantom.exit(1);
        }
        if (args[2]) {
            page.evaluate(function (timeout) {
                if (window.jasmine) {
                    jasmine.getEnv().defaultTimeoutInterval = timeout;
                }
            }, args[2]);
        }
        page.evaluate(function () {
            if (window.girderTest) {
                girderTest.promise.done(function () {
                    // Allow Jasmine to compare RegExp using toEqual, toHaveBeenCalledWith, etc.
                    jasmine.getEnv().addEqualityTester(function (a, b) {
                        if (a instanceof RegExp && jasmine.isString_(b)) {
                            return a.test(b);
                        } else if (b instanceof RegExp && jasmine.isString_(a)) {
                            return b.test(a);
                        }
                        return jasmine.undefined;
                    });

                    jasmine.getEnv().execute();
                }).fail(function (err) {
                    window.callPhantom({
                        action: 'exit',
                        code: 1,
                        errorMessage: err
                    });
                });
            } else {
                window.callPhantom({
                    action: 'exit',
                    code: 1,
                    errorMessage: 'Girder test utils not loaded into phantom env.'
                });
            }
        });
    }
};

/* Sometimes phantom fails when loading many resources.  I think this is this
 * known issue: https://github.com/ariya/phantomjs/issues/10652.  Adding a
 * resource timeout and then reloading the resource works around the problem.
 */
page.settings.resourceTimeout = 15000;

page.onResourceTimeout = function (request) {
    /* Ignore timeout of the notification stream */
    if (request.url.indexOf('/api/v1/notification/stream') > 0) {
        return;
    }
    console.log('Resource timed out.  (#' + request.id + '): ' + JSON.stringify(request));
    console.log('PHANTOM_TIMEOUT');
    /* The exit code doesn't get sent back from here, so setting this to a
     * non-zero value doesn't seem to have any benefit. */
    phantom.exit(0);
};

page.open(pageUrl, function (status) {
    if (status !== 'success') {
        console.error('Could not load page: ' + pageUrl);
        phantom.exit(1);
    }
    // In phantom 2.x, calling console.error triggers page.onError, which we don't want.
    page.evaluate(function () {
        console.error = console.log;
    });
});
