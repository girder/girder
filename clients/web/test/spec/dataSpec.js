/**
 * As of v1.9.9, phantomJS does not correctly support sending Blobs in XHRs,
 * and the FormData API is extremely limited (i.e. does not support anything
 * other than "append"). We fake the chunk request to get around this by
 * wrapping XHR.prototype.send.
 */

var uploadData;
/* used for resume testing */
var uploadDataExtra = 0;

(function (impl) {
    XMLHttpRequest.prototype.send = function (data) {
        if (data && data instanceof FormData) {
            data = new FormData();
            data.append('offset', 0);
            data.append('uploadId', girder._uploadId);
            /* Note that this appears to fail if uploadData contains certain
             * characters, such as LF. */
            if (uploadData.length && !uploadDataExtra)
                data.append('chunk', uploadData);
            else
                data.append('chunk', new Array(
                    uploadData+1+uploadDataExtra).join('-'));
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
 *                    want to resume, then resume.
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

            $('.g-resume-upload').click();
        });
    }

    waitsFor(function () {
        return $('.modal-content:visible').length === 0 &&
               $('.g-item-list-entry').length === orig_len+1;
    }, 'the upload to finish');
    /* css animations need to process, so this wait seems fairly certain */
    waits(200);

    window.callPhantom({action: 'uploadCleanup'});
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

        waitsFor(function () {
            return $('.g-save-folder').length > 0;
        }, 'the edit folder save button to appear');

        runs(function () {
            $('button.g-save-folder').click();
        });
    });

    it('upload a file into the current folder', function () {
        _testUpload('clients/web/test/testFile.txt');
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

    it('upload a large file', function () {
        /* Use a file greater than the S3 chunk size of 32Mb.  There is a bug
         * in phantomjs that fails to parse the response headers from the
         * multipart uploads.  As such, when this is run on the S3 assetstore,
         * this test will fail unless phantomjs is run with
         * --web-security=false */
        _testUpload(1024 * 1024 * 33);
    });

    it('upload a large file requiring resume', function () {
        _testUpload(1024 * 1024 * 33, true);
    });
});
