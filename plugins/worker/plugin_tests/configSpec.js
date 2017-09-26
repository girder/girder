/* globals girderTest, describe, it, waitsFor, runs, expect */

girderTest.importPlugin('jobs');
girderTest.importPlugin('worker');
girderTest.startApp();

$(function () {
    describe('Test the settings page', function () {
        it('create the admin user', function () {
            girderTest.createUser(
                'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword')();
        });
        it('change the worker settings', function () {
            waitsFor(function () {
                return $('a.g-nav-link[g-target="admin"]').length > 0;
            }, 'admin console link to load');
            runs(function () {
                $('a.g-nav-link[g-target="admin"]').click();
            });
            waitsFor(function () {
                return $('.g-plugins-config').length > 0;
            }, 'the admin console to load');
            runs(function () {
                $('.g-plugins-config').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('input.g-plugin-switch[key="worker"]').length > 0;
            }, 'the plugins page to load');
            runs(function () {
                expect($('.g-plugin-config-link[g-route="plugins/worker/config"]').length > 0);
                $('.g-plugin-config-link[g-route="plugins/worker/config"]').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('#g-worker-settings-form input').length > 0;
            }, 'worker settings to be shown');

            runs(function () {
                $('#g-worker-broker').val('amqp://guest@localhost/');
                $('#g-worker-backend').val('amqp://guest@127.0.0.1/');
                $('#g-worker-api-url').val('http://127.0.0.1:8080/api/v1');
                $('#g-worker-direct-path').trigger('click');
                $('#g-worker-settings-form input.btn-primary').click();
            });
            runs(function () {
                // go back to the plugins page
                $('.g-plugins-link').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('input.g-plugin-switch[key="worker"]').length > 0;
            }, 'the plugins page to load');
            runs(function () {
                expect($('.g-plugin-config-link[g-route="plugins/worker/config"]').length > 0);
                $('.g-plugin-config-link[g-route="plugins/worker/config"]').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('#g-worker-settings-form input').length > 0;
            }, 'worker settings to be shown');

            runs(function () {
                expect($('#g-worker-broker').val()).toBe('amqp://guest@localhost/');
                expect($('#g-worker-backend').val()).toBe('amqp://guest@127.0.0.1/');
                expect($('#g-worker-api-url').val()).toBe('http://127.0.0.1:8080/api/v1');
                expect($('#g-worker-direct-path').prop('checked')).toBe(true);
            }, 'worker settings to change');
            girderTest.waitForLoad();
        });
    });
});
