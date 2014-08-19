/**
 * Copyright Kitware Inc.
 *
 * This is the phantomjs runtime script that invokes the girder app in test
 * mode. The test mode page is built with grunt and lives at:
 * clients/web/static/built/testEnv.html. It then executes a jasmine spec within
 * the context of that test application, and afterwards runs our custom coverage
 * handler on the coverage data.
 */

if (phantom.args.length < 2) {
    console.error('Usage: phantomjs phantom_jasmine_runner.js <page> <spec> [<covg_output>]');
    console.error('  <page> is the path to the HTML page to load');
    console.error('  <spec> is the path to the jasmine spec to run.');
    console.error('  <covg_output> is the path to a file to write coverage into.');
    phantom.exit(2);
}

var pageUrl = phantom.args[0];
var spec = phantom.args[1];
var coverageOutput = phantom.args[2] || null;
var page = new WebPage();
var accumCoverage = false;

var fs = require('fs');

if (coverageOutput) {
    fs.write(coverageOutput, '', 'w');
}

var terminate = function () {
    var status = this.page.evaluate(function () {
        if (window.jasmine_phantom_reporter.status === "success") {
            return window.coverageHandler.handleCoverage(window._$blanket);
        }
        else {
            return false;
        }
    });

    if (status) {
        phantom.exit(0);
    }
    else {
        phantom.exit(1);
    }
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
            fs.workingDirectory + '/' + imageFile + '</DartMeasurementFile>');
        return;
    }

    if (accumCoverage && coverageOutput) {
        try {
            fs.write(coverageOutput, msg, 'a');
        } catch (e) {
            console.log('Exception writing coverage results: ', e);
        }
    }
    else {
        console.log(msg);
    }
    if (msg === 'ConsoleReporter finished') {
        accumCoverage = true;
        return terminate();
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
    phantom.exit(1);
};

page.onLoadFinished = function (status) {
    if (status !== 'success') {
        console.error('Page load failed');
        phantom.exit(1);
    }

    page.injectJs('coverageHandler.js');
    if(!page.injectJs(spec)) {
        console.error('Could not load test spec into page: ' + spec);
        phantom.exit(1);
    }
};

page.open(pageUrl, function (status) {
    if (status !== 'success') {
        console.error('Could not load page: ' + pageUrl);
        phantom.exit(1);
    }
});
