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
        expect($('.g-global-nav-li span').text()).not.toContain('Admin Console');
    });

    it('register a user (first is admin)',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));

    it('Admin console should show when admin is logged in', function () {
        expect($('.g-global-nav-li span').text()).toContain('Admin Console');
    });

    it('logout from admin account', girderTest.logout());

    it('No admin console directly after admin logs out', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin Console');
    });

    it('register a (normal user)',
        girderTest.createUser('johndoe',
                              'john.doe@email.com',
                              'John',
                              'Doe',
                              'password!'));

    it('No admin console when logging in as a normal user', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin Console');
    });
});
