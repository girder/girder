/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({
        el: 'body',
        parentView: null
    });
    girder.events.trigger('g:appload.after');
});

describe('Create an admin and non-admin user', function () {
    var link, registeredUsers = [];

    it('register a user (first is admin)',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!',
                              registeredUsers));

    it('logout', girderTest.logout());

    it('register another user',
        girderTest.createUser('nonadmin',
                              'nonadmin@email.com',
                              'Not',
                              'Admin',
                              'password!',
                              registeredUsers));

    it('view the users on the user page and click on one', function () {
        girderTest.goToUsersPage()();
        runs(function () {
            expect($('.g-user-list-entry').length).toBe(2);
            expect($('a.g-user-link').text()).toBe('Admin AdminNot Admin');
        });

        runs(function () {
            $("a.g-user-link:contains('Admin Admin')").click();
        });

        waitsFor(function () {
            return $('.g-user-name').text() === 'Admin Admin';
        }, 'user page to appear');

        girderTest.waitForLoad();
        // check for actions menu
        runs(function () {
            expect($("button:contains('Actions')").length).toBe(0);
        });
    });

    it('check for no admin checkbox on user settings page', function () {
        girderTest.goToCurrentUserSettings()();
        runs(function () {
            expect($('input#g-admin').length).toBe(0);
        });
    });

    it('check redirect to front page after logout from user page', function () {
        girderTest.logout()();
        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });

    it('check redirect to front page after logout from users list page', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();
        girderTest.goToUsersPage()();
        girderTest.logout()();
        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });

    it('check for admin checkbox on admin user settings page', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();
        girderTest.goToCurrentUserSettings()();
        runs(function () {
            expect($('input#g-admin').length).toBe(1);
        });
        runs(function () {
            $('#g-firstName').val('');
            $('button').has('.icon-edit').click();
        });
        waitsFor(function () {
            return $('#g-user-info-error-msg').text() === 'First name must not be empty.';
        }, 'Name error to occur');
        runs(function () {
            $('#g-firstName').val('Admin');
            $('button').has('.icon-edit').click();
        });
        waitsFor(function () {
            return $('#g-user-info-error-msg').text() === '';
        }, 'error to vanish');
    });

    it("test changing other user's password", function () {
        runs(function () {
            girder.router.navigate('useraccount/' + registeredUsers[1].id + '/password',
                                   {trigger: true});
        });

        waitsFor(function () {
            return $('input#g-password-new:visible').length > 0;
        }, 'password input to appear');
        girderTest.waitForLoad();

        runs(function () {
            expect($('.g-user-description').text()).toBe('nonadmin');
            expect($('#g-password-old').length).toBe(0);

            $('#g-password-new,#g-password-retype').val('a new password');
            $('#g-password-change-form button[type="submit"]').click();
        });

        waitsFor(function () {
            return $('#g-alerts-container .alert-success').length > 0 &&
                   $('#g-password-new').val() === '';
        }, 'password change to complete');
    });

    it('test reset password', function () {
        girderTest.logout()();
        runs(function () {
            $('.g-login').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('input#g-login').length > 0;
        }, 'login dialog to appear');
        runs(function () {
            $('.g-forgot-password').click();
        });
        waitsFor(function () {
            return $('.g-password-reset-explanation').length > 0;
        }, 'forgotton password dialog to appear');
        girderTest.waitForDialog();
        runs(function () {
            $('#g-email').val('invalid@email.com');
            $('#g-reset-password-button').click();
        });
        waitsFor(function () {
            return $('.g-validation-failed-message').text().indexOf(
                'not registered') >= 0;
        }, 'error message to appear');
        runs(function () {
            $('#g-email').val('nonadmin@email.com');
            $('#g-reset-password-button').click();
        });
        girderTest.waitForLoad();
        runs(function () {
            console.log('__FETCHEMAIL__');
        });
        waitsFor(function () {
            var msg = window.callPhantom({
                action: 'fetchEmail',
                suffix: girderTest.getCallbackSuffix()});
            if (!msg || msg.indexOf('<a href="') <0) {
                return false;
            }
            link = msg.substr(msg.indexOf('<a href="')+9);
            link = link.substr(0, link.indexOf('"'));
            link = link.substr(link.indexOf('#'));
            return link;
        }, 'email to be received');
    });
    it('Use reset link', function () {
        runs(function(){
            girderTest.testRoute(link, false, function () {
                return $('#g-password-new:visible').length > 0 &&
                       $('#g-password-old:visible').length === 0;
            });
        });
        runs(function () {
            $('#g-password-new').val('newpassword');
            $('#g-password-retype').val('newpassword2');
            $('button').has('.icon-lock').click();
        });
        waitsFor(function () {
            return $('#g-password-change-error-msg').text() === 'Passwords do not match, try again.';
        }, 'password match error to occur');
        runs(function () {
            $('#g-password-new').val('new');
            $('#g-password-retype').val('new');
            $('button').has('.icon-lock').click();
        });
        waitsFor(function () {
            return $('#g-password-change-error-msg').text() === 'Password must be at least 6 characters.';
        }, 'password match error to occur');
        runs(function () {
            $('#g-password-new').val('newpassword');
            $('#g-password-retype').val('newpassword');
            $('button').has('.icon-lock').click();
        });
        waitsFor(function () {
            return $('#g-password-new').val() === '';
        }, 'new password to be accepted');
        runs(function () {
            window.callPhantom({action: 'uploadCleanup',
                                suffix: girderTest._uploadSuffix});
        });
    });
});
