/* globals girderTest, describe, expect, it, runs, waitsFor  */

girderTest.addScripts([
    '/static/built/plugins/provenance/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    describe('test the provenance plugin', function () {
        it('create the admin user', girderTest.createUser(
            'provenance', 'provenance@girder.org', 'Provenance', 'Plugin',
            'testpassword'));
        it('change the provenance settings', function () {
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
                return $('input.g-plugin-switch[key="provenance"]').length > 0;
            }, 'the plugins page to load');
            runs(function () {
                expect($('.g-plugin-config-link[g-route="plugins/provenance/config"]').length > 0);
                $('.g-plugin-config-link[g-route="plugins/provenance/config"]').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('input#provenance').length > 0;
            }, 'resource list setting to be shown');
            runs(function () {
                $('input#provenance').val('folder');
                $('#g-provenance-form input.btn-primary').click();
            });
            waitsFor(function () {
                var resp = girder.rest.restRequest({
                    path: 'system/setting',
                    type: 'GET',
                    data: {key: 'provenance.resources'},
                    async: false
                });
                return resp.responseText === '"folder"';
            }, 'provenance settings to change');
            girderTest.waitForLoad();
        });
    });
});
