/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});

describe('Test group actions', function () {

    it('register a user (first is admin)',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));

    it('go to groups page', girderTest.goToGroupsPage());

    it('check that groups page is blank', function () {
        runs(function () {
            expect($('.g-group-list-entry').length).toBe(0);
        });
    });

    it('Create a private group',
       girderTest.createGroup('privGroup', 'private group', false));

    it('go back to groups page', girderTest.goToGroupsPage());

    it('Create a public group',
       girderTest.createGroup('pubGroup', 'public group', true));

    it('Open edit dialog and check url state', function () {
        waitsFor(function () {
            return $('.g-group-actions-button:visible').length === 1;
        }, 'the group actions button to appear');

        waits(300);

        runs(function () {
            $('.g-group-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-edit-group:visible').length === 1;
        }, 'the group edit action to appear');

        runs(function () {
            $('.g-edit-group').click();
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-18) === '/roles?dialog=edit';
        }, 'the url state to change');

        waitsFor(function () {
            return $('a.btn-default').text() === 'Cancel';
        }, 'the cancel button to appear');

        runs(function () {
            $('a.btn-default').click();
        });
    });

    it('go back to groups page', girderTest.goToGroupsPage());

    it('check that the groups page has both groups for admin', function () {
        waitsFor(function () {
            return $('.g-group-list-entry').length === 2;
        }, 'the two groups to show up');

        runs(function () {
            expect($('.g-group-list-entry').text().match('privGroup').length === 1);
            expect($('.g-group-list-entry').text().match('pubGroup').length === 1);
            expect($('.g-group-list-entry').text().match('private group').length === 1);
            expect($('.g-group-list-entry').text().match('public group').length === 1);
        });
    });

    it('logout to become anonymous', girderTest.logout());

    it('check that the groups page has only the public groups for anon', function () {
        waitsFor(function () {
            return $('.g-group-list-entry').length === 1;
        }, 'the two groups to show up');

        runs(function () {
            expect($('.g-group-list-entry').text().match('pubGroup').length === 1);
            expect($('.g-group-list-entry').text().match('public group').length === 1);
        });
    });

});
