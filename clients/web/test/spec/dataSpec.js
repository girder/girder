/**
 * As of v1.9.9, phantomJS does not correctly support sending Blobs in XHRs,
 * and the FormData API is extremely limited (i.e. does not support anything
 * other than "append"). We fake the chunk request to get around this by
 * wrapping XHR.prototype.send.
 */

/* used for adjusting minimum upload size */
var minUploadSize;


/* Set the minimum chunk size in the server settings, the upload handler, and
 *  the S3 asset store handler.
 * :param minSize: the new minimum size.  If null, revert to the original
 *                 minimums.
 */
function _setMinimumChunkSize(minSize) {
    if (!minUploadSize)
    {
        minUploadSize = {UPLOAD_CHUNK_SIZE: girder.UPLOAD_CHUNK_SIZE};
        var resp = girder.restRequest({
            path: 'system/setting',
            type: 'GET',
            data: {key: 'core.upload_minimum_chunk_size'},
            async: false
        });
        minUploadSize.setting = resp.responseText;
    }
    if (!minSize)
    {
        var uploadChunkSize = minUploadSize.UPLOAD_CHUNK_SIZE;
        var settingSize = minUploadSize.setting;
    }
    else
    {
        var uploadChunkSize = minSize;
        var settingSize = minSize;
    }
    girder.UPLOAD_CHUNK_SIZE = uploadChunkSize;
    girder.restRequest({
        path: 'system/setting',
        type: 'PUT',
        data: {key: 'core.upload_minimum_chunk_size', value: settingSize},
        async: false
    });
}

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
    var app = new girder.App({
        el: 'body',
        parentView: null
    });
    girder.events.trigger('g:appload.after');
});

describe('Create a data hierarchy', function () {
    var folder;

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
        });
        girderTest.waitForLoad();
        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(1);
            $('a.g-my-folders').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('li.g-folder-list-entry').length > 0;
        }, 'my folders list to display');

        runs(function () {
            expect($('a.g-folder-list-link:first').text()).toBe('Private');
            expect($('.g-folder-privacy:first').text()).toBe('Private');
            $('a.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();

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
        girderTest.waitForDialog();

        runs(function () {
            $('input#g-name').val("John's subfolder");
            $('#g-description').val(' Some description');

            $('.g-save-folder').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('li.g-folder-list-entry').length > 0;
        }, 'the new folder to display in the list');

        runs(function () {
            expect($('a.g-folder-list-link:first').text()).toBe(
                "John's subfolder");
            expect($('.g-folder-privacy:first').text()).toBe('Private');
            $('a.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();

        runs(function () {
            $('a.g-edit-folder').click();
        });

        waitsFor(function () {
            return $('textarea#g-description').val() === 'Some description';
        }, 'the edit folder dialog to appear');
        girderTest.waitForDialog();

        waitsFor(function () {
            return $('.g-save-folder').length > 0;
        }, 'the edit folder save button to appear');

        runs(function () {
            $('button.g-save-folder').click();
        });
        girderTest.waitForLoad();
    });

    it('upload a file into the current folder', function () {
        girderTest.testUpload('clients/web/test/testFile.txt');
    });

    it('download the file', function () {
        runs(function () {
            $('.g-item-list-link').click();
        });

        waitsFor(function () {
            return $('.g-file-list-link').length === 1;
        }, 'the item page to display the file list');

        runs(function () {
            girderTest._redirect = null;
            window.location.assign($('a.g-file-list-link').attr('href'));
        });

        waitsFor(function () {
            return girderTest._redirect !== null;
        }, 'redirect to the file download URL');

        runs(function () {
            expect(/^http:\/\/localhost:.*\/api\/v1\/file\/.+\/download$/.test(
                girderTest._redirect)).toBe(true);
        });
    });

    it('search using quick search box', function () {
        runs(function () {
            $('.g-quick-search-container input.g-search-field')
                .val('john').trigger('input');
        });
        waitsFor(function () {
            return $('.g-quick-search-container .g-search-results')
                .hasClass('open');
        }, 'search to return');
        runs(function () {
            $('.g-quick-search-container input.g-search-field')
                .val('').trigger('input');
        });
        waitsFor(function () {
            return $('.g-quick-search-container .g-search-results')
                .hasClass('open') == false;
        }, 'search to return');
        runs(function () {
            $('.g-quick-search-container input.g-search-field')
                .val('john').trigger('input');
        });
        waitsFor(function () {
            return $('.g-quick-search-container .g-search-results')
                .hasClass('open');
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
    it('keyboard control of quick search box', function () {
        function sendKeyDown(code, selector) {
            var e = $.Event("keydown");
            e.which = code;
            $(selector).trigger(e);
        }
        runs(function () {
            for (var i=1; i<=4; i++) {
                $('.g-quick-search-container input.g-search-field')
                    .val('john'.substr(0, i)).trigger('input');
            }
        });
        waitsFor(function () {
            return $('.g-quick-search-container .g-search-results')
                .hasClass('open');
        }, 'search to return');
        runs(function () {
            sendKeyDown(38, '.g-quick-search-container input.g-search-field');
            sendKeyDown(38, '.g-quick-search-container input.g-search-field');
            sendKeyDown(38, '.g-quick-search-container input.g-search-field');
            sendKeyDown(40, '.g-quick-search-container input.g-search-field');
            sendKeyDown(40, '.g-quick-search-container input.g-search-field');
            sendKeyDown(13, '.g-quick-search-container input.g-search-field');
            expect(Backbone.history.fragment).toBe(
                'user/' + girder.currentUser.get('_id'));
        });
    });

    it('upload a file without an extension', function () {
        waitsFor(function () {
            return $('li.g-folder-list-entry').length > 0;
        }, 'my folders list to display');

        runs(function () {
            expect($('a.g-folder-list-link:first').text()).toBe('Private');
            expect($('.g-folder-privacy:first').text()).toBe('Private');
            $('a.g-folder-list-link:first').click();
        });

        waitsFor(function () {
            return $('.g-loading-block').length == 0;
        }, 'for all blocks to load');

        girderTest.testUpload('clients/web/test/testFile2');
    });

    it('upload another file by size', function () {
        girderTest.testUpload(11);
    });

    it('upload requiring resume', function () {
        girderTest.testUpload(1024 * 32, true);
    });

    it('upload requiring resume that is aborted', function () {
        girderTest.testUpload(1024 * 32, 'abort');
    });

    it('upload a large file', function () {
        /* Use a file greater than the twice the S3 chunk size and greater than
         * twice the general upload chunk size.  We do this by artificially
         * changing these chunk sizes to make the test faster.  There is a bug
         * in phantomjs that fails to parse the response headers from the
         * multipart uploads.  As such, when this is run on the S3 assetstore,
         * this test will fail unless phantomjs is run with
         * --web-security=false */
        _setMinimumChunkSize(1024 * 256);
        girderTest.testUpload(1024 * 513);
    });
    it('upload a large file requiring resume', function () {
        _setMinimumChunkSize(1024 * 256);
        girderTest.testUpload(1024 * 513, true);
    });

    it('download a folder', function () {
        waitsFor(function () {
            return $('.g-folder-actions-button:visible').length === 1;
        }, 'the folder actions button to appear');
        runs(function () {
            $('.g-folder-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-download-folder:visible').length === 1;
        }, 'the folder down action to appear');
        runs(function () {
            girderTest._redirect = null;
            window.location.assign($('a.g-download-folder').attr('href'));
        });
        waitsFor(function () {
            return girderTest._redirect !== null;
        }, 'redirect to the resource download URL');
        runs(function () {
            expect(/^http:\/\/localhost:.*\/api\/v1\/folder\/.+\/download$/.test(
                girderTest._redirect)).toBe(true);
        });
    });
    it('download checked items', function () {
        var redirect, widget;
        /* select a folder and the first item */
        runs(function () {
            $('.g-list-checkbox').slice(0,2).click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-download-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            widget = girder.events._events['g:navigateTo'][0].ctx.bodyView.
                     hierarchyWidget;
            /* We don't expose the hierarchy view directly, so we have to reach
             * through some internal objects to get to it */
            spyOn(widget, 'redirectViaForm').
                  andCallFake(function (method, url, data) {
                redirect = {method: method, url: url, data: data};
                widget.redirectViaForm.originalValue(
                    method, 'javascript: void(0)', data);
            });
            $('a.g-download-checked').click();
        });
        runs(function () {
            expect(widget.redirectViaForm).toHaveBeenCalled();
            expect(redirect.method).toBe('GET');
            expect(/^http:\/\/localhost:.*\/api\/v1\/resource\/download.*/.
                   test(redirect.url)).toBe(true);
            expect(/{"folder":.*,"item":.*}/.test(redirect.data.resources)).
                   toBe(true);
        });
    });
    it('copy picked items', function () {
        runs(function () {
            $('.g-select-all').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox:not(:checked)').length == 0 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'all items to be checked');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-pick-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-pick-checked').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-copy-picked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-copy-picked').click();
        });
        waitsFor(function () {
            return $('.g-task-progress-title').text() == 'Copying resources';
        }, 'progress to be shown');
        waitsFor(function () {
            return $('.g-list-checkbox').length == 12;
        }, 'items to be copied');
    });
    it('move picked items', function () {
        runs(function () {
            $('.g-list-checkbox:last').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox:checked').length == 1 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'one item to be checked');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-pick-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-pick-checked').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        /* select a second item and add it to our picked list */
        runs(function () {
            $('.g-select-all').click();
            $('.g-select-all').click();
            $('.g-list-checkbox').slice(-2,-1).click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox:checked').length == 1 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'one item to be checked');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-pick-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-pick-checked').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        /* add the first folder to our picked list */
        runs(function () {
            $('.g-select-all').click();
            $('.g-select-all').click();
            $('.g-list-checkbox:first').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox:checked').length == 1 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'one item to be checked');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-pick-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-pick-checked').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        /* Navigate to the user page and make sure move and copy are no longer
         * offered, since we can't move items to a user. */
        runs(function () {
            $('.g-breadcrumb-link:first').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox').length == 2 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'just two folders to be visible');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0;
        }, 'checked actions menu');
        runs(function () {
            expect($('a.g-copy-picked').length).toBe(0);
            expect($('a.g-move-picked').length).toBe(0);
            expect($('a.g-clear-picked').length).toBe(1);
            $('a.g-folder-list-link:last').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-list-checkbox').length == 0 &&
                   $('.g-empty-parent-message').length == 1;
        }, 'Public folder to be visible');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-copy-picked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-move-picked').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox').length == 3;
        }, 'items to be copied');
        /* Change the permission of the moved folder, then navigate back to the
         * private folder, to save the public data for permissions tests. */
        runs(function () {
            $('a.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-list-checkbox').length == 1;
        }, 'subfolder to be shown');
        girderTest.folderAccessControl('private', 'public');
        runs(function () {
            $('.g-breadcrumb-link:first').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox').length == 2 &&
                   $('.g-checked-actions-button:disabled').length == 1;
        }, 'just two folders to be visible and no picked items');
        runs(function () {
            $('a.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-list-checkbox').length == 9;
        }, 'private list should be down to nine items');
    });
    it('delete checked items', function () {
        runs(function () {
            $('.g-select-all').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox:not(:checked)').length == 0 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'all items to be checked');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-delete-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-delete-checked').click();
        });

        waitsFor(function () {
            return $('#g-confirm-button:visible').length > 0;
        }, 'delete confirmation to appear');
        runs(function () {
            $('#g-confirm-button').click();
        });

        waitsFor(function () {
            return $('.g-list-checkbox').length == 0;
        }, 'items to be deleted');
        runs(function () {
            window.callPhantom({action: 'uploadCleanup',
                                suffix: girderTest._uploadSuffix});
        });
    });
    /* Create a second user so that we can test move/copy permissions */
    it('logout from first account', girderTest.logout('logout from first account'));
    it('register a second user',
        girderTest.createUser('janedoe',
                              'jane.doe@email.com',
                              'Jane',
                              'Doe',
                              'password!'));
    it('test copy permissions', function () {
        var oldPicked;
        runs(function () {
            $('a.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-list-checkbox').length == 3;
        }, 'public folder to be shown');
        /* Select one item and make sure we can't copy or move */
        runs(function () {
            $('.g-list-checkbox:last').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox:checked').length == 1 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'one item to be checked');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-pick-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-pick-checked').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-clear-picked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            expect($('a.g-move-picked').length).toBe(0);
            expect($('a.g-copy-picked').length).toBe(0);
            oldPicked = girder.pickedResources;
            $('.g-clear-picked').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        /* Select one folder and make sure we can't move or copy. */
        runs(function () {
            $('.g-select-all').click();
            $('.g-select-all').click();
            $('.g-list-checkbox:first').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox:checked').length == 1 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'one folder to be checked');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-pick-checked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            $('a.g-pick-checked').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-clear-picked').length > 0;
        }, 'checked actions menu');
        runs(function () {
            expect($('a.g-move-picked').length).toBe(0);
            expect($('a.g-copy-picked').length).toBe(0);
            $('#g-app-body-container').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        girderTest.goToUsersPage()();
        runs(function () {
            $('.g-user-link:first').click();
        });
        waitsFor(function () {
            return $('.g-list-checkbox').length == 2;
        }, 'user folders to be shown');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-clear-picked').length > 0;
        }, 'checked actions menu');
        /* We should be able to copy but not move */
        runs(function () {
            expect($('a.g-move-picked').length).toBe(0);
            expect($('a.g-copy-picked').length).toBe(1);
            $('#g-app-body-container').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu:visible').length == 0;
        }, 'checked actions menu to hide');
        runs(function () {
            /* Skip a bunch of UI actiosn to more quickly get back to have one
             * item selected. */
            girder.pickedResources = oldPicked;
            $('a.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-empty-parent-message:visible').length === 1;
        }, 'empty folder to be shown');
        runs(function () {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-clear-picked').length > 0;
        }, 'checked actions menu');
        /* We should be able to copy but not move */
        runs(function () {
            expect($('a.g-move-picked').length).toBe(0);
            expect($('a.g-copy-picked').length).toBe(1);
            $('#g-app-body-container').click();
        });
    });

    it('logout from second user', girderTest.logout('logout from second user'));
});

describe('Test FileModel static upload functions', function () {
    var folder, item;

    it('test prep - register a user', girderTest.createUser('dbowman',
                                                            'dbowman@nasa.gov',
                                                            'David',
                                                            'Bowman',
                                                            'jupiter'));

    it('test prep - create top level folder', function () {
        runs(function () {
            var _folder = new girder.models.FolderModel({
                parentType: 'user',
                parentId: girder.currentUser.get('_id'),
                name: 'top level folder'
            }).on('g:saved', function () {
                folder = _folder;
            }).save();
        });

        waitsFor(function () {
            return !!folder && folder.get('_id');
        }, 'folder creation');
    });

    it('test prep - create item', function () {
        runs(function () {
            var _item = new girder.models.ItemModel({
                folderId: folder.get('_id'),
                name: 'an item'
            }).on('g:saved', function () {
                item = _item;
            }).save();
        });

        waitsFor(function () {
            return !!item;
        }, 'item creation');
    });

    var oldPrototype = window.Blob.prototype;
    window.BlobBuilder = window.BlobBuilder || window.WebKitBlobBuilder;
    window.Blob = function (data) {
        var builder = new BlobBuilder();
        _.each(data, function (d) {
            builder.append(d);
        });
        return builder.getBlob();
    };
    window.Blob.prototype = oldPrototype;

    it('test FileModel.uploadToFolder()', function () {
        var ok = false, text, filename, speech, fileModel, file;

        filename = 'hal.txt';

        // TODO: replace this with the "correct" mechanism for handling text
        // with Jasmine (cc @manthey).
        girderTest._uploadData = speech = "Just what do you think you're doing, Dave?";

        runs(function () {
            fileModel = new girder.models.FileModel();
            fileModel.uploadToFolder(folder.get('_id'), speech, filename, 'text/plain');
        });

        waitsFor(function () {
            return !fileModel.isNew();
        }, "file model to become valid");

        runs(function () {
            var item;

            item = girder.restRequest({
                path: '/item',
                type: 'GET',
                data: {
                    folderId: folder.get("_id"),
                    text: filename,
                },
                async: false
            });

            item = item && item.responseJSON && item.responseJSON[0];

            file = girder.restRequest({
                path: '/item/' + item._id + '/files',
                type: 'GET',
                async: false
            });

            file = file && file.responseJSON && file.responseJSON[0];

            if (file) {
                resp = girder.restRequest({
                    path: '/file/' + file._id + '/download',
                    type: 'GET',
                    dataType: 'text',
                    async: false
                });

                text = resp.responseText;
            }
        });

        waitsFor(function () {
            return file._id === fileModel.get("_id") && file.name === filename && text === speech;
        });
    });

    it('test FileModel.uploadToItem()', function () {
        var ok = false, text, filename, speech, file, fileModel;

        filename = 'dave.txt';

        // TODO: replace this with the "correct" mechanism for handling text
        // with Jasmine (cc @manthey).
        girderTest._uploadData = speech = "Open the pod bay doors, HAL.";

        runs(function () {
            fileModel = new girder.models.FileModel();
            fileModel.uploadToItem(item.get('_id'), speech, filename, 'text/plain');
        });

        waitsFor(function () {
            return !fileModel.isNew();
        });

        runs(function () {
            file = girder.restRequest({
                path: '/item/' + item.get('_id') + '/files',
                type: 'GET',
                async: false
            });

            file = file && file.responseJSON && file.responseJSON[0];

            if (file) {
                resp = girder.restRequest({
                    path: '/file/' + file._id + '/download',
                    type: 'GET',
                    dataType: 'text',
                    async: false
                });

                text = resp.responseText;
            }
        });

        waitsFor(function () {
            return file._id === fileModel.get("_id") && file.name === filename && text === speech;
        });
    });

    it('logout from test account', girderTest.logout('logout from test account'));
});
