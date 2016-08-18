/**
 * Copyright Kitware Inc.
 *
 * This is the PhantomJS runtime script that invokes the Girder app in test
 * mode. The test mode page is built with grunt and lives at:
 * clients/web/static/built/testing/testEnv.html. It then executes a Jasmine spec within
 * the context of that test application, and afterwards runs our custom coverage
 * handler on the coverage data.
 */
/* globals phantom, WebPage, jasmine, girderTest */

var system = require('system');
var args = phantom.args ? phantom.args : system.args.slice(1);

if (args && args.length < 2) {
    console.error('Usage: phantomjs phantom_jasmine_runner.js <page> <spec> [<covg_output> [<default jasmine timeout>]');
    console.error('  <page> is the path to the HTML page to load');
    console.error('  <spec> is the path to the Jasmine spec to run.');
    console.error('  <covg_output> is the path to a file to write coverage into.');
    console.error('  <default Jasmine timeout> is in milliseconds.');
    phantom.exit(2);
}

var env = system.env;

var pageUrl = args[0];
var spec = args[1];
var coverageOutput = args[2] || null;
var page = new WebPage();
var accumCoverage = false;

var fs = require('fs');
require('event-source/global');

if (coverageOutput) {
    fs.write(coverageOutput, '', 'w');
}

var terminate = function () {
    if (!coverageOutput) {
        // setTimeout(function () {
        //     phantom.exit(0);
        // }, 0);
        phantom.exit(0);
        return true;
    }
    var status = this.page.evaluate(function () {
        if (window.jasmine_phantom_reporter.status === 'success') {
            return window.coverageHandler.handleCoverage(window._$blanket);
        } else {
            return false;
        }
    });

    if (status) {
        phantom.exit(0);
    } else {
        phantom.exit(1);
    }
    return status;
};

// Set decent viewport size for screenshots.
page.viewportSize = {
    width: 1024,
    height: 769
};

page.onConsoleMessage = function (msg) {
    if (msg.indexOf('__SCREENSHOT__') === 0) {
        var imageFile = msg.substring('__SCREENSHOT__'.length) || 'phantom_screenshot.png';
        page.render(imageFile);
        console.log('Created screenshot: ' + imageFile);

        console.log('<DartMeasurementFile name="PhantomScreenshot" type="image/png">' +
            fs.workingDirectory + fs.separator + imageFile + '</DartMeasurementFile>');

        if (env['PHANTOMJS_OUTPUT_AJAX_TRACE'] === undefined ||
            env['PHANTOMJS_OUTPUT_AJAX_TRACE'] === 1 ||
            env['PHANTOMJS_OUTPUT_AJAX_TRACE'] === true) {
            console.log('Dumping ajax trace:');
            console.log(page.evaluate(function () {
                return JSON.stringify(girderTest.ajaxLog(true), null, '  ');
            }));
        }
        return;
    }

    if (accumCoverage && coverageOutput) {
        try {
            fs.write(coverageOutput, msg, 'a');
        } catch (e) {
            console.log('Exception writing coverage results: ', e);
        }
    } else {
        console.log(msg);
    }
    if (msg === 'ConsoleReporter finished') {
        accumCoverage = true;
        return terminate();
    }
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
    console.log('Saved phantom_error_screenshot.png');
    console.log('<DartMeasurementFile name="PhantomErrorScreenshot" type="image/png">' +
        fs.workingDirectory + '/phantom_error_screenshot.png</DartMeasurementFile>');
    page.render('phantom_error_screenshot.png');
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
        if (coverageOutput) {
            page.injectJs('coverageHandler.js');
        }
        if (!page.injectJs(spec)) {
            console.error('Could not load test spec into page: ' + spec);
            phantom.exit(1);
        }
        if (args[3]) {
            page.evaluate(function (timeout) {
                if (window.jasmine) {
                    jasmine.getEnv().defaultTimeoutInterval = timeout;
                }
            }, args[3]);
        }
    }
};

/* Sometimes phantom fails when loading many resources.  I think this is this
 * known issue: https://github.com/ariya/phantomjs/issues/10652.  Adding a
 * resource timeout and then reloading the resource works around the problem.
 */
page.settings.resourceTimeout = 15000;

page.onResourceTimeout = function (request) {
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
});
