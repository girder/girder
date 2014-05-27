/**
 * This is the phantomjs runtime script that invokes the girder app in test
 * mode. The test mode page is built with grunt and lives at:
 * clients/web/static/built/testEnv.html. It then executes a jasmine spec within
 * the context of that test application.
 */
var PhantomJasmineRunner = function () {
    function PhantomJasmineRunner (page, exitFunc) {
        this.page = page;
        this.exitFunc = exitFunc || phantom.exit;
    }

    PhantomJasmineRunner.prototype.getStatus = function () {
        return this.page.evaluate(function (threshold) {
            if (window.jasmine_phantom_reporter.status === "success"){
                return window.travisCov.check(window._$blanket, {
                    threshold: threshold
                });
            }
            else {
                return false;
            }
        }, coverageThreshold);
    };

    PhantomJasmineRunner.prototype.terminate = function () {
        if (this.getStatus()) {
            return this.exitFunc(0);
        }
        else {
            return this.exitFunc(1);
        }
    };

    return PhantomJasmineRunner;
}();

if (phantom.args.length < 2) {
    console.error('Usage: phantomjs phantom_jasmine_runner.js <page> <spec>');
    console.error('  <page> is the path to the HTML page to load');
    console.error('  <spec> is the path to the jasmine spec to run.');
    phantom.exit(2);
}

var pageUrl = phantom.args[0];
var spec = phantom.args[1];
var coverageThreshold = phantom.args[2] || 5;
var page = new WebPage();
var runner = new PhantomJasmineRunner(page);

page.onConsoleMessage = function (msg) {
  console.log(msg);
  if (msg === 'ConsoleReporter finished') {
    return runner.terminate();
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

    page.injectJs('travisCov.js');
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

