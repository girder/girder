/**
 * As of v1.9.9, phantomJS does not correctly support sending Blobs in XHRs,
 * and the FormData API is extremely limited (i.e. does not support anything
 * other than "append"). We fake the chunk request to get around this by
 * wrapping XHR.prototype.send.
 */
(function (impl) {
    XMLHttpRequest.prototype.send = function (data) {
        if(data && data instanceof FormData) {
            data = new FormData();
            data.append('offset', 0);
            data.append('uploadId', girder._uploadId);
            data.append('chunk', 'hello');
        }
        impl.call(this, data);
    };
} (XMLHttpRequest.prototype.send));

/**
 * Intercept window.location.assign calls so we can test the behavior of,
 * e.g. download directives that occur from js.
 */
(function (impl) {
    window.location.assign = function (url) {
        girderTest._redirect = url;
    };
} (window.location.assign));

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

    it('upload a file into the current folder', function () {
        runs(function () {
            $('.g-upload-here-button').click();
        });

        waitsFor(function () {
            return $('.g-drop-zone:visible').length > 0;
        }, 'the upload dialog to appear');

        runs(function () {
            // Incantation that causes the phantom environment to send us a File.
            $('#g-files').parent().removeClass('hide');
            console.log('__ATTACH__#g-files clients/web/test/testFile.txt');
        });

        waitsFor(function () {
            return $('.g-overall-progress-message i.icon-ok').length > 0;
        }, 'the file to be received');

        runs(function () {
            $('#g-files').parent().addClass('hide');
            $('.g-start-upload').click();
        });

        waitsFor(function () {
            return $('.modal-content:visible').length === 0 &&
                   $('.g-item-list-entry').length === 1;
        }, 'the upload to finish');
    });

    it('download the file', function () {
        runs(function () {
            // The backdrops don't get properly removed on phantomJS so we do it manually
            $('.modal-backdrop').remove();
            $('.g-item-list-link').click();
        });

        waitsFor(function () {
            return $('.g-file-list-link').length === 1;
        }, 'the item page to display the file list');

        runs(function () {
            girderTest._redirect = null;
            $('.g-file-list-link').click();
        });

        waitsFor(function () {
            return girderTest._redirect !== null;
        }, 'redirect to the file download URL');

        runs(function () {
            expect(/^http:\/\/localhost:.*\/api\/v1\/file\/.+\/download\?token=.*$/.test(
                girderTest._redirect)).toBe(true);
        });
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
