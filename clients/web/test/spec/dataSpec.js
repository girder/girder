/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});

describe('Create a data hierarchy', function () {
    it('register a user', function () {
        expect(girder.currentUser).toBe(null);

        waitsFor(function () {
            return $('.g-register').length > 0;
        }, 'girder app to render');

        runs(function () {
            $('.g-register').click();
        });

        waitsFor(function () {
            return $('input#g-email').length > 0;
        }, 'register dialog to appear');

        runs(function () {
            $('#g-login').val('johndoe');
            $('#g-email').val('john.doe@email.com');
            $('#g-firstName').val('John');
            $('#g-lastName').val('Doe');
            $('#g-password,#g-password2').val('password!');
            $('#g-register-button').click();
        });

        waitsFor(function () {
            return $('.modal-dialog:visible').length === 0;
        }, 'registration dialog to disappear');

        runs(function () {
            expect(girder.currentUser).not.toBe(null);
            expect(girder.currentUser.name()).toBe('John Doe');
            expect(girder.currentUser.get('login')).toBe('johndoe');
        });
    });

    it('create a folder', function () {
        expect($('#g-user-action-menu.open').length).toBe(0);
        $('.g-user-text>a:first').click();
        expect($('#g-user-action-menu.open').length).toBe(1);
        $('a.g-my-folders').click();

        waitsFor(function () {
            return $('li.g-folder-list-entry').length > 0;
        }, 'my folders list to display');

        runs(function () {
            expect($('a.g-folder-list-link:first').text()).toBe('Private');
            expect($('.g-folder-privacy:first').text()).toBe('Private');
            $('a.g-folder-list-link:first').click();
        });

        waitsFor(function () {
            return $('ol.breadcrumb>li.active').text() === 'Private';
        }, 'descending into Private folder');

        runs(function () {
            expect($('.g-empty-parent-message:visible').length).toBe(1);
            $('.g-folder-actions-button').click();
            $('.g-create-subfolder').click();
        });

        waitsFor(function () {
            return $('input#g-name').length > 0;
        }, 'create folder dialog to appear');

        runs(function () {
            $('input#g-name').val("John's subfolder");
            $('.g-save-folder').click();
        });

        waitsFor(function () {
            return $('li.g-folder-list-entry').length > 0;
        }, 'the new folder to display in the list');

        runs(function () {
            expect($('a.g-folder-list-link:first').text()).toBe("John's subfolder");
            expect($('.g-folder-privacy:first').text()).toBe('Private');
        });
    });

    it('search using quick search box', function () {
        $('.g-quick-search-container input.g-search-field')
            .val('john').trigger('input');

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
