describe('Test the swagger pages', function () {
    it('Test swagger', function () {
        waitsFor(function () {
            return $('#operations-tag-system').length > 0;
        }, 'swagger docs to appear');
        runs(function () {
            expect($('#operations-tag-system a span').text()).toBe('system');
        });
        runs(function () {
            $('#operations-tag-system a').trigger('click');
        });
        waitsFor(function () {
            return $('#operations-system-system_getVersion_version:visible').length > 0;
        }, 'end points to be visible');
        runs(function () {
            $('#operations-system-system_getVersion_version a').trigger('click');
        });
        waitsFor(function () {
            return $('#operations-system-system_getVersion_version .execute:visible').length > 0;
        }, 'version execute button to be visible');
        runs(function () {
            $('#operations-system-system_getVersion_version .execute').trigger('click');
        });
        waitsFor(function () {
            return $('#operations-system-system_getVersion_version .highlight-code code').text().indexOf('release') >= 0;
        }, 'version information was returned');
    });
});

var jasmineEnv = jasmine.getEnv();
var consoleReporter = new jasmine.ConsoleReporter();
window.jasmine_phantom_reporter = consoleReporter;
jasmineEnv.addReporter(consoleReporter);
jasmineEnv.execute();
