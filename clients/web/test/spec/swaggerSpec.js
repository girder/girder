function jasmineTests() {
    var jasmineEnv = jasmine.getEnv();
    var consoleReporter = new jasmine.ConsoleReporter();
    window.jasmine_phantom_reporter = consoleReporter;
    jasmineEnv.addReporter(consoleReporter);
    function waitAndExecute() {
        if (!jasmineEnv.currentRunner().suites_.length) {
            window.setTimeout(waitAndExecute, 10);
            return;
        }
        jasmineEnv.execute();
    }

    waitAndExecute();

    describe('Test the swagger pages', function () {
        it('Test swagger', function () {
            waitsFor(function () {
                return $('li#resource_system.resource').length > 0;
            }, 'swagger docs to appear');
            runs(function () {
                $('li#resource_system.resource .heading h2 a').click();
            });
            waitsFor(function () {
                return $('#system_getVersion:visible').length > 0;
            }, 'end points to be visible');
            runs(function () {
                $('#system_getVersion h3 a').click();
            });
            waitsFor(function () {
                return $('#system_getVersion .sandbox_header input.submit[name="commit"]:visible').length > 0;
            }, 'version try out button to be visible');
            runs(function () {
                $('#system_getVersion .sandbox_header input.submit[name="commit"]').click();
            });
            waitsFor(function () {
                return $('#system_getVersion .response_body.json').text().indexOf('apiVersion') >= 0;
            }, 'version information was returned');
        });
    });

}

$(function () {
    $.getScript('/static/built/testing-no-cover.min.js', jasmineTests);
});
