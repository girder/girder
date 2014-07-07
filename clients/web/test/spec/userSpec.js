/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});

describe('Create an admin and non-admin user', function () {
    it('register a user (first is admin)',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));

    it('logout', girderTest.logout());

    it('register another user',
        girderTest.createUser('nonadmin',
                              'nonadmin@email.com',
                              'Not',
                              'Admin',
                              'password!'));

    it('go to users page', girderTest.goToUsersPage());

    it('view the users on the user page and click on one', function () {
        runs(function () {
            expect($('.g-user-list-entry').length).toBe(2);
            expect($('a.g-user-link').text()).toBe('Not AdminAdmin Admin');
        });

        runs(function () {
            $("a.g-user-link:contains('Admin Admin')").click();
        });

        waitsFor(function () {
            return $('.g-user-name').text() === 'Admin Admin';
        }, 'user page to appear');

        // check for actions menu
        runs(function () {
            expect($("button:contains('Actions')").length).toBe(0);
        });
    });

    it('go to current user settings page',
        girderTest.goToCurrentUserSettings());

    it('check for lack of admin checkbox', function () {
        runs(function () {
            expect($('input#g-admin').length).toBe(0);
        });
    });

    it('logout', girderTest.logout());

    it('check redirect to users page', function () {
        waitsFor(function () {
            return Backbone.history.fragment === 'users';
        }, 'redirect to users');
    });

    it('login as admin',
        girderTest.login('admin',
                         'Admin',
                         'Admin',
                         'adminpassword!'));

    it('go to current user settings page',
        girderTest.goToCurrentUserSettings());

    it('check for admin checkbox', function () {
        runs(function () {
            expect($('input#g-admin').length).toBe(1);
        });
    });
});
