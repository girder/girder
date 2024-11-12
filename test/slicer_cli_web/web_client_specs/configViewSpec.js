girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var slicer;
girderTest.promise.done(function () {
    slicer = girder.plugins.slicer_cli_web;
});

girderTest.startApp();

$(function () {
    describe('settings', function () {
        it('login as admin user', function () {
            girderTest.login('admin', 'Admin', 'Admin', 'password')();
        });
        var folderId = ''; // TODO
        it('change the large_image settings', function () {
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
                return $('.g-plugin-config-link').length > 0;
            }, 'the plugins page to load');
            runs(function () {
                expect($('.g-plugin-config-link[g-route="plugins/slicer_cli_web/config"]').length > 0);
                $('.g-plugin-config-link[g-route="plugins/slicer_cli_web/config"]').click();
            });
            girderTest.waitForLoad();

            waitsFor(function () {
                return $('#g-slicer-cli-web-form input').length > 0;
            }, 'resource list setting to be shown');

            // modify the form
            runs(function () {
                $('#g-slicer-cli-web-upload-folder').val(folderId);
                // save
                $('#g-slicer-cli-web-form input.btn-primary').click();
            });
            waitsFor(function () {
                var resp = girder.rest.restRequest({
                    url: 'system/setting',
                    method: 'GET',
                    data: {
                        list: JSON.stringify(['slicer_cli_web.task_folder'])
                    },
                    async: false
                });
                var settings = resp.responseJSON;
                return (settings['slicer_cli_web.task_folder'] === folderId);
            }, 'slicer_cli_web settings to change');
            girderTest.waitForLoad();
        });
    });
});
