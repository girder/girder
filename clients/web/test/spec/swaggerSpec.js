/* globals jasmine, runs, waitsFor, describe, it */

$(function () {
    describe('Test the swagger pages', function () {
        it('Test swagger', function () {
            waitsFor(function () {
                return $('li#resource_system.resource').length > 0;
            }, 'swagger docs to appear');
            runs(function () {
                expect($('li#resource_system.resource .heading h2 a').text()).toBe('system');
            });
            // There seems to be some delay between the link showing and when swaggerUi actually
            // binds the event handler. We don't have a good hook into that binding, so we hack
            // it with a 0.1s delay instead.
            waits(100);
            runs(function () {
                $('li#resource_system.resource .heading h2 a').click();
            });
            waitsFor(function () {
                return $('#system_system_getVersion:visible').length > 0;
            }, 'end points to be visible');
            runs(function () {
                $('#system_system_getVersion h3 a').click();
            });
            waitsFor(function () {
                return $('#system_system_getVersion .sandbox_header input.submit:visible').length > 0;
            }, 'version try out button to be visible');
            runs(function () {
                $('#system_system_getVersion .sandbox_header input.submit').click();
            });
            waitsFor(function () {
                return $('#system_system_getVersion .response_body.json').text().indexOf('apiVersion') >= 0;
            }, 'version information was returned');
        });
    });

    var jasmineEnv = jasmine.getEnv();
    var consoleReporter = new jasmine.ConsoleReporter();
    window.jasmine_phantom_reporter = consoleReporter;
    jasmineEnv.addReporter(consoleReporter);
    jasmineEnv.execute();
});
