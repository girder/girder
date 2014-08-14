/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});

describe('Create an admin and non-admin user', function () {

    it('No admin console without logging in', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin console');
    });

    it('register a user (first is admin)',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));

    it('Admin console should show when admin is logged in', function () {
        expect($('.g-global-nav-li span').text()).toContain('Admin console');
    });

    it('logout from admin account', girderTest.logout());

    it('No admin console directly after admin logs out', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin console');
    });

    it('register a (normal user)',
        girderTest.createUser('johndoe',
                              'john.doe@email.com',
                              'John',
                              'Doe',
                              'password!'));

    it('No admin console when logging in as a normal user', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin console');
    });
});

describe('Test the settings page', function () {
    it('Logout', girderTest.logout());
    it('Login as admin', girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
    it('Go to settings page', function () {
        runs(function () {
            $("a.g-nav-link[g-target='admin']").click();
        });

        waitsFor(function () {
            return $('.g-server-config').length > 0;
        }, 'admin page to load');

        runs(function () {
            $('.g-server-config').click();
        });

        waitsFor(function () {
            return $('input#g-cookie-lifetime').length > 0;
        }, 'settings page to load');
    });

    it('Settings should display their expected values', function () {
        expect($('#g-cookie-lifetime').val()).toBe('');
        expect($('#g-smtp-host').val()).toMatch(/^localhost:500/);
        expect($('#g-email-from-address').val()).toBe('');
        expect($('#g-registration-policy').val()).toBe('open');
    });
});
