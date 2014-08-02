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
        girderTest.createUser('seconduser',
                              'seconduser@email.com',
                              'Second',
                              'User',
                              'password!'));

    it('logout', girderTest.logout());

    it('register a third user',
        girderTest.createUser('nonadmin',
                              'nonadmin@email.com',
                              'Not',
                              'Admin',
                              'password!'));

    it('go to users page', girderTest.goToUsersPage());

    it('view the users on the user page and click on one', function () {
        runs(function () {
            expect($('.g-user-list-entry').length).toBe(3);
        });

        runs(function () {
            $("a.g-user-link:contains('Not Admin')").click();
        });

        waitsFor(function () {
            return $('.g-user-name').text() === 'Not Admin';
        }, 'user page to appear');

        // check for actions menu
        runs(function () {
            expect($("button:contains('Actions')").length).toBe(1);
        });
    });

    it('create an item in the public folder of the user', function () {

        waitsFor(function () {
            return $('a.g-folder-list-link:contains(Public):visible').length === 1;
        }, 'the public folder to be clickable');

        runs(function () {
            $('a.g-folder-list-link:contains(Public)').click();
        });

        waitsFor(function () {
            return $('.g-empty-parent-message:visible').length === 1 &&
                   $('.g-folder-actions-button:visible').length === 1;
        }, 'message that the folder is empty');

        runs(function () {
            $('.g-folder-actions-button:visible').click();
        });

        waitsFor(function () {
            return $('a.g-create-item:visible').length === 1;
        }, 'create item option is clickable');

        runs(function () {
            $('.g-create-item:visible').click();
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-18) === '?dialog=itemcreate';
        }, 'the url state to change');

        waitsFor(function () {
            return $('a.btn-default:visible').text() === 'Cancel';
        }, 'the cancel button of the item create dialog to appear');

        runs(function () {
            $('#g-name').val('Test Item Name');
            $('#g-description').val('Test Item Description');
            $('.g-save-item').click();
        });

        waitsFor(function () {
            return $('a.g-item-list-link:contains(Test Item Name)').length === 1;
        }, 'the new item to appear in the list');

        runs(function () {
            $('a.g-item-list-link:contains(Test Item Name)').click();
        });

        waitsFor(function () {
            return $('.g-item-name:contains(Test Item Name)').length === 1;
        }, 'the item page to load');

        runs(function () {
            expect($('.g-item-name').text()).toBe("Test Item Name");
            expect($('.g-item-description').text()).toBe("Test Item Description");
        });
    });
});
