/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});

describe('Create a data hierarchy', function () {
    it('register a user',
        girderTest.createUser('johndoe',
                              'john.doe@email.com',
                              'John',
                              'Doe',
                              'password!'));

    it('create a folder', function () {
        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(0);
            $('.g-user-text>a:first').click();
            expect($('#g-user-action-menu.open').length).toBe(1);
            $('a.g-my-folders').click();
        });

        waitsFor(function () {
            return $('li.g-folder-list-entry').length > 0;
        }, 'my folders list to display');

        runs(function () {
            expect($('a.g-folder-list-link:first').text()).toBe('Private');
            expect($('.g-folder-privacy:first').text()).toBe('Private');
            $('a.g-folder-list-link:first').click();
        });

        waitsFor(function () {
            return $('ol.breadcrumb>li.active').text() === 'Private' &&
                   $('.g-empty-parent-message:visible').length === 1;
        }, 'descending into Private folder');

        runs(function () {
            $('.g-folder-actions-button').click();
            $('.g-create-subfolder').click();
        });

        waitsFor(function () {
            return $('input#g-name').length > 0;
        }, 'create folder dialog to appear');

        runs(function () {
            $('input#g-name').val("John's subfolder");
            $('#g-description').val(' Some description');

            $('.g-save-folder').click();
        });

        waitsFor(function () {
            return $('li.g-folder-list-entry').length > 0;
        }, 'the new folder to display in the list');

        runs(function () {
            expect($('a.g-folder-list-link:first').text()).toBe("John's subfolder");
            expect($('.g-folder-privacy:first').text()).toBe('Private');
            $('a.g-folder-list-link:first').click();
        });

        runs(function () {
            $('a.g-edit-folder').click();
        });

        waitsFor(function () {
            return $('textarea#g-description').val() === 'Some description';
        }, 'the edit folder dialog to appear');
    });

    it('search using quick search box', function () {
        runs(function () {
            $('.g-quick-search-container input.g-search-field')
                .val('john').trigger('input');
        });

        waitsFor(function () {
            return $('.g-quick-search-container .g-search-results').hasClass('open');
        }, 'search to return');

        runs(function () {
            var results = $('.g-quick-search-container li.g-search-result');
            expect(results.length).toBe(2);

            expect(results.find('a[resourcetype="folder"]').length).toBe(1);
            expect(results.find('a[resourcetype="user"]').length).toBe(1);

            results.find('a[resourcetype="user"]').click();

            expect(Backbone.history.fragment).toBe(
                'user/' + girder.currentUser.get('_id'));
        });
    });
});
