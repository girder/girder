/* globals girderTest, describe, it, runs, expect, waitsFor */

girderTest.addCoveredScripts([
    // '/plugins/autojoin/web_client/main.js',
    // '/plugins/autojoin/web_client/routes.js',
    // '/plugins/autojoin/web_client/views/ConfigView.js'
]);
girderTest.addScripts([
    '/static/built/plugins/autojoin/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    describe('test the autojoin ui', function () {
        it('register an admin', girderTest.createUser(
            'admin', 'admin@example.com', 'Joe', 'Admin', 'password'
        ));

        var group1, group2, group3;

        it('go to groups page', girderTest.goToGroupsPage());
        it('create a group', girderTest.createGroup('group1', '', false));
        runs(function () {
            group1 = window.location.hash.split('/')[1];
        });

        it('go to groups page', girderTest.goToGroupsPage());
        it('create a group', girderTest.createGroup('group2', '', false));
        runs(function () {
            group2 = window.location.hash.split('/')[1];
        });

        it('go to groups page', girderTest.goToGroupsPage());
        it('create a group', girderTest.createGroup('group3', '', false));
        runs(function () {
            group3 = window.location.hash.split('/')[1];
        });

        it('go to auto join plugin settings', function () {
            waitsFor(function () {
                return $('a[g-target="admin"]:visible').length > 0;
            }, 'admin console link to display');

            runs(function () {
                $('a[g-target="admin"]:visible').click();
            });

            waitsFor(function () {
                return $('.g-plugins-config:visible').length > 0;
            }, 'admin console to display');

            runs(function () {
                $('.g-plugins-config:visible').click();
            });

            waitsFor(function () {
                return $('a[g-route="plugins/autojoin/config"]:visible').length > 0;
            }, 'plugins page to display');

            runs(function () {
                $('a[g-route="plugins/autojoin/config"]:visible').click();
            });

            waitsFor(function () {
                return $('.g-autojoin-container:visible').length > 0;
            }, 'auto join config to display');

            waitsFor(function () {
                return girder.rest.numberOutstandingRestRequests() === 0;
            }, 'rest requests to finish');
        });

        it('create auto join rules', function () {
            runs(function () {
                $('#g-autojoin-pattern').val('@kitware.com');
                $('#g-autojoin-group').val(group1);
                $('#g-autojoin-level').val(2);
                $('#g-autojoin-add').click();
            });
            waitsFor(function () {
                return girder.rest.numberOutstandingRestRequests() === 0;
            }, 'rest requests to finish');

            runs(function () {
                $('#g-autojoin-pattern').val('@example.com');
                $('#g-autojoin-group').val(group2);
                $('#g-autojoin-level').val(1);
                $('#g-autojoin-add').click();
            });
            waitsFor(function () {
                return girder.rest.numberOutstandingRestRequests() === 0;
            }, 'rest requests to finish');

            runs(function () {
                $('#g-autojoin-pattern').val('@example.com');
                $('#g-autojoin-group').val(group3);
                $('#g-autojoin-level').val(0);
                $('#g-autojoin-add').click();
            });
            waitsFor(function () {
                return girder.rest.numberOutstandingRestRequests() === 0;
            }, 'rest requests to finish');

            runs(function () {
                $('#g-autojoin-save').click();
            });
            waitsFor(function () {
                return girder.rest.numberOutstandingRestRequests() === 0;
            }, 'rest requests to finish');
        });

        it('logout', girderTest.logout());
        it('register a user', girderTest.createUser(
            'user1', 'user1@example.com', 'Joe', 'User', 'password'
        ));
        it('go to groups page', girderTest.goToGroupsPage());
        it('verify correct groups', function () {
            expect($('.g-group-title:contains("group1")').length).toBe(0);
            expect($('.g-group-title:contains("group2")').length).toBe(1);
            expect($('.g-group-title:contains("group3")').length).toBe(1);
        });

        it('logout', girderTest.logout());
        it('register a user', girderTest.createUser(
            'user2', 'user2@kitware.com', 'Joe', 'User', 'password'
        ));
        it('go to groups page', girderTest.goToGroupsPage());
        it('verify correct groups', function () {
            expect($('.g-group-title:contains("group1")').length).toBe(1);
            expect($('.g-group-title:contains("group2")').length).toBe(0);
            expect($('.g-group-title:contains("group3")').length).toBe(0);
        });
    });
});
