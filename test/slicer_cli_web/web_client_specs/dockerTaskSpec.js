/* globals girderTest, describe, it, expect, waitsFor, runs */

girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

girderTest.startApp();

function login(user, password) {
    girderTest.waitForLoad('login wait 1');
    runs(function () {
        $('.g-login').click();
    });

    girderTest.waitForDialog('login wait 2');
    runs(function () {
        $('#g-login').val(user || 'user');
        $('#g-password').val(password || 'password');
        $('#g-login-button').click();
    });

    waitsFor(function () {
        return $('.g-user-dropdown-link').length > 0;
    }, 'user to be logged in');
    girderTest.waitForLoad('login wait 3');
}

$(function () {
    describe('Test the slicer_cli_web plugin', function () {
        it('change the slicer_cli_web settings', function () {
            login('admin', 'password');
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
            runs(function () {
                $('.g-open-browser').eq(0).trigger('click');
            });
            girderTest.waitForDialog();
            runs(function () {
                $('select#g-root-selector').val($('select#g-root-selector option').eq(1).val()).trigger('change');
            });
            waitsFor(function () {
                return $('.g-folder-list-link:contains("Public")').length > 0;
            }, 'the public folder to be visible');
            runs(function () {
                $('.g-folder-list-link:contains("Public")').trigger('click');
            });
            waitsFor(function () {
                return $('#g-selected-model').val() === 'Public';
            }, 'the public folder to be selected');
            runs(function () {
                $('.g-submit-button').trigger('click');
            });
            girderTest.waitForLoad();
            runs(function () {
                $('.btn[value="Save"]').trigger('click');
            });
            girderTest.waitForLoad();
        });
        it('import the small docker', function () {
            runs(function () {
                $('#g-slicer-cli-web-image').val('girder/slicer_cli_web:small');
                $('.btn[value="Import Image"]').trigger('click');
            });
            waitsFor(function () {
                var resp = girder.rest.restRequest({
                    url: 'resource/lookup',
                    method: 'GET',
                    data: {path: '/user/admin/Public/girder\\-slicer_cli_web/small/Example1'},
                    async: false
                });
                return resp && resp.responseJSON && resp.responseJSON['_id'];
            }, 'Wait for Example1 to be imported.');
        });
        it('navigate to the Example1 task', function () {
            runs(function () {
                expect($('#g-user-action-menu.open').length).toBe(0);
                $('.g-user-text>a').first().trigger('click');
            });
            girderTest.waitForLoad();

            runs(function () {
                expect($('#g-user-action-menu.open').length).toBe(1);
                $('a.g-my-folders').trigger('click');
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                // The page may be loaded, but the folder list still populates asynchronously
                return $('.g-folder-list>.g-folder-list-entry').length === 2;
            });

            runs(function () {
                $('a.g-folder-list-link').last().trigger('click');
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('a.g-folder-list-link:contains("girder/slicer_cli_web")').length > 0;
            });

            runs(function () {
                $('a.g-folder-list-link:contains("girder/slicer_cli_web")').trigger('click');
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('a.g-folder-list-link:contains("small")').length > 0;
            });

            runs(function () {
                $('a.g-folder-list-link:contains("small")').trigger('click');
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('a.g-item-list-link:contains("Example1")').length > 0;
            });

            runs(function () {
                $('a.g-item-list-link:contains("Example1")').trigger('click');
            });
            girderTest.waitForLoad();
        });
        it('check that the expected controls are present', function () {
            runs(function () {
                expect($('.s-panel-title-container').length >= 6).toBe(true);
            });
        });
        it('A panel can be toggled', function () {
            runs(function () {
                expect($('#integerVariable:visible').length).toBe(1);
                $('.s-panel-title:contains("Scalar Parameters")').trigger('click');
            });
            waitsFor(function () {
                return $('#integerVariable:visible').length === 0;
            });
            runs(function () {
                expect($('#integerVariable:visible').length).toBe(0);
            });
        });
        // Add more tests here
    });
});
