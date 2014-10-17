/**
 * As of v1.9.9, phantomJS does not correctly support sending Blobs in XHRs,
 * and the FormData API is extremely limited (i.e. does not support anything
 * other than "append"). We fake the chunk request to get around this by
 * wrapping XHR.prototype.send.
 */

var uploadData;
/* used for resume testing */
var uploadDataExtra = 0;
/* used for adjusting minimum upload size */
var minUploadSize;

(function (impl) {
    FormData.prototype.append = function (name, value, filename) {
        this.vals = this.vals || {};
        if (filename)
            this.vals[name+'_filename'] = value;
        this.vals[name] = value;
        impl.call(this, name, value, filename);
    };
} (FormData.prototype.append));

(function (impl) {
    XMLHttpRequest.prototype.send = function (data) {
        if (data && data instanceof FormData) {
            var newdata = new FormData();
            newdata.append('offset', data.vals.offset);
            newdata.append('uploadId', data.vals.uploadId);
            var len = data.vals.chunk.size;
            /* Note that this appears to fail if uploadData contains certain
             * characters, such as LF. */
            if (uploadData.length && uploadData.length==len &&
                    !uploadDataExtra)
                newdata.append('chunk', uploadData);
            else
                newdata.append('chunk',
                                new Array(len+1+uploadDataExtra).join('-'));
            data = newdata;
        }
        else if (data && data instanceof Blob) {
            if (uploadDataExtra)
            {
                /* Our mock S3 server will take extra data, so break it by
                 * adding a faulty copy header.  This will throw an error so we
                 * can test resumes. */
                this.setRequestHeader('x-amz-copy-source', 'bad_value');
            }
            if (uploadData.length && uploadData.length==data.size &&
                    !uploadDataExtra)
                data = uploadData;
            else
                data = new Array(data.size+1+uploadDataExtra).join('-');
        }
        impl.call(this, data);
    };
} (XMLHttpRequest.prototype.send));

function _testUpload(uploadItem, needResume)
/* Upload a file and make sure it lands properly.
 * :param uploadItem: either the path to the file to upload or an integer to
 *                    create and upload a temporary file of that size.
 * :param needResume: if true, upload a partial file so that we are asked if we
 *                    want to resume, then resume.  If 'abort', then abort the
 *                    upload instead of resuming it.
 */
{
    var orig_len;

    waitsFor(function () {
        return $('.g-upload-here-button').length > 0;
    }, 'the upload here button to appear');

    runs(function () {
        orig_len = $('.g-item-list-entry').length;
        $('.g-upload-here-button').click();
    });

    waitsFor(function () {
        return $('.g-drop-zone:visible').length > 0 &&
               $('.modal-dialog:visible').length > 0;
    }, 'the upload dialog to appear');

    runs(function () {
        if (needResume)
            uploadDataExtra = 1024 * 20;
        else
            uploadDataExtra = 0;

        // Incantation that causes the phantom environment to send us a File.
        $('#g-files').parent().removeClass('hide');
        var params = {action: 'uploadFile', selector: '#g-files'};
        if (uploadItem === parseInt(uploadItem))
        {
            params.size = uploadItem;
        }
        else
        {
            params.path = uploadItem;
        }
        uploadData = window.callPhantom(params);
    });

    waitsFor(function () {
        return $('.g-overall-progress-message i.icon-ok').length > 0;
    }, 'the file to be received');

    runs(function () {
        $('#g-files').parent().addClass('hide');
        $('.g-start-upload').click();
    });

    if (needResume)
    {
        waitsFor(function () {
            return $('.g-resume-upload:visible').length > 0;
        }, 'the resume link to appear');
        runs(function () {
            uploadDataExtra = 0;

            if (needResume == 'abort') {
                $('.btn-default').click();
                orig_len -= 1;
            } else {
                $('.g-resume-upload').click();
            }
        });
    }

    waitsFor(function () {
        return $('.modal-content:visible').length === 0 &&
               $('.g-item-list-entry').length === orig_len+1;
    }, 'the upload to finish');
    girderTest.waitForLoad();

    window.callPhantom({action: 'uploadCleanup'});
}

function _setMinimumChunkSize(minSize)
/* Set the minimum chunk size in the server settings, the upload handler, and
 *  the S3 asset store handler.
 * :param minSize: the new minimum size.  If null, revert to the original
 *                 minimums.
 */
{
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
            expect($('a.g-folder-list-link:first').text()).toBe("John's subfolder");
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
        _testUpload('clients/web/test/testFile.txt');
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

        _testUpload('clients/web/test/testFile2');
    });

    it('upload another file by size', function () {
        _testUpload(11);
    });

    it('upload requiring resume', function () {
        _testUpload(1024 * 32, true);
    });

    it('upload requiring resume that is aborted', function () {
        _testUpload(1024 * 32, 'abort');
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
        _testUpload(1024 * 513);
    });
    it('upload a large file requiring resume', function () {
        _setMinimumChunkSize(1024 * 256);
        _testUpload(1024 * 513, true);
    });

    it('download checked items', function () {
        /* select a folder and the first item */
        runs(function() {
            $('.g-list-checkbox').slice(0,2).click();
        });
        waitsFor(function() {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-download-checked').length > 0;
        }, 'checked actions menu');
        runs(function() {
            girderTest._redirect = null;
            $('a.g-download-checked').click();
        });
        waitsFor(function () {
            return girderTest._redirect !== null;
        }, 'redirect to the resource download URL');
        runs(function () {
            expect(/^http:\/\/localhost:.*\/api\/v1\/resource\/download\?resources=.*$/.test(
                girderTest._redirect)).toBe(true);
        });
    });
    it('delete checked items', function () {
        runs(function() {
            $('.g-select-all').click();
        });
        waitsFor(function() {
            return $('.g-list-checkbox:not(:checked)').length == 0 &&
                   $('.g-checked-actions-button:disabled').length == 0;
        }, 'all items to be checked');
        runs(function() {
            $('.g-checked-actions-button').click();
        });
        waitsFor(function() {
            return $('.g-checked-actions-menu').length > 0 &&
                   $('a.g-delete-checked').length > 0;
        }, 'checked actions menu');
        runs(function() {
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
    });
});
