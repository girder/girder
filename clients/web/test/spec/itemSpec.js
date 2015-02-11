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

function _editItem(button, buttonText)
/* Show the item edit dialog and click a button.
 * :param button: the jquery selector for the button.
 * :param buttonText: the expected text of the button.
 */
{
    waitsFor(function () {
        return $('.g-item-actions-button:visible').length === 1;
    }, 'the item actions button to appear');

    runs(function () {
        $('.g-item-actions-button').click();
    });

    waitsFor(function () {
        return $('.g-edit-item:visible').length === 1;
    }, 'the item edit action to appear');

    runs(function () {
        $('.g-edit-item').click();
    });

    waitsFor(function () {
        return Backbone.history.fragment.slice(-16) === '?dialog=itemedit';
    }, 'the url state to change');
    girderTest.waitForDialog();

    waitsFor(function () {
        return $('#g-name').val() !== '';
    }, 'the dialog to be populated');

    waitsFor(function () {
        return $(button).text() === buttonText;
    }, 'the button to appear');

    runs(function () {
        $(button).click();
    });
    girderTest.waitForLoad();
}

describe('Test item creation, editing, and deletion', function () {
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
        girderTest.waitForDialog();

        runs(function () {
            $('#g-name').val('Test Item Name');
            $('#g-description').val('Test Item Description');
            $('.g-save-item').click();
        });

        waitsFor(function () {
            return $('a.g-item-list-link:contains(Test Item Name)').length === 1;
        }, 'the new item to appear in the list');
        girderTest.waitForLoad();

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

    it('Open edit dialog and check url state', function () {
        _editItem('a.btn-default', 'Cancel');
    });

    it('Add, edit, and delete metadata for the item', girderTest.testMetadata());

    it('Open edit dialog and save the item', function () {
        _editItem('button.g-save-item', 'Save');
    });

    it('Edit files', function () {
        var fileId1;

        runs(function() {
            var id = window.location.hash.split('/')[1].split('?')[0];
            /* Create a link file */
            girder.restRequest({
                path: 'file', type: 'POST',
                data: {parentType: 'item', parentId: id, name: 'File 1',
                       linkUrl: 'http://nowhere.com/file1'
                },
                async: false
            });
        });
        girderTest.waitForLoad();

        // Upload a file into the item
        waitsFor(function () {
            return $('.g-upload-into-item:visible').length === 1;
        }, 'the upload files to item action to appear');

        runs(function () {
            $('.g-upload-into-item').click();
        });
        girderTest.waitForDialog();

        runs(function () {
            _prepareTestUpload();
            girderTest._uploadDataExtra = 0;
            girderTest.sendFile('clients/web/test/testFile.txt');
        });

        waitsFor(function () {
            return $('.g-overall-progress-message i.icon-ok').length > 0;
        }, 'the filesChanged event to happen');

        runs(function () {
            $('#g-files').parent().addClass('hide');
            $('.g-start-upload').click();
        });

        waitsFor(function () {
            return $('.modal-content:visible').length === 0 &&
                   $('.g-file-list-entry').length === 2;
        }, 'the upload to finish');
        girderTest.waitForLoad();

        /* Easy way to reload the item page */
        _editItem('button.g-save-item', 'Save');
        /* Try to edit each file in turn.  They must have different ids */
        waitsFor(function () {
            return $('.g-file-list-entry .g-update-info').length == 2;
        }, 'the files to be listed');
        runs(function() {
            $('.g-file-list-entry .g-update-info').eq(0).click();
        });
        waitsFor(function () {
            return window.location.hash.split('?dialog=fileedit&').length == 2;
        }, 'the url state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#g-name').val() !== '';
        }, 'the dialog to be populated');
        waitsFor(function () {
            return $(document.activeElement).attr('id') == 'g-name';
        }, 'the name to have focus');
        waitsFor(function () {
            return $('a.btn-default').text() === 'Cancel';
        }, 'the cancel button to appear');
        runs(function () {
            $('#g-name').val('');
            $('button.g-save-file').click();
        });
        waitsFor(function () {
            return $('.modal-dialog .g-validation-failed-message').text() == 'File name must not be empty.';
        }, 'error message to appear');
        runs(function () {
            fileId1 = window.location.hash.split('dialogid=')[1];
            $('a.btn-default').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-file-list-entry .g-update-info').length == 2;
        }, 'the files to be listed');
        runs(function() {
            $('.g-file-list-entry .g-update-info').eq(1).click();
        });
        waitsFor(function () {
            return window.location.hash.split('?dialog=fileedit&').length == 2;
        }, 'the url state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#g-name').val() !== '';
        }, 'the dialog to be populated');
        waitsFor(function () {
            return $('button.g-save-file').text() === 'Save';
        }, 'the save button to appear');
        runs(function () {
            expect(window.location.hash.split('dialogid=')[1] == fileId1)
                .toBe(false);
            $('button.g-save-file').click();
        });
        girderTest.waitForLoad();

        // Delete the file
        var fileListLength;
        runs(function () {
            fileListLength = $('.g-file-list-entry').length;
            $('.g-file-actions-container:first .g-delete-file').click();
        });

        waitsFor(function () {
            return $('.modal-body').text().indexOf('Are you sure you want to delete the file') !== -1;
        }, 'the deletion confirmation prompt to appear');
        girderTest.waitForDialog();

        runs(function () {
            $('#g-confirm-button').click();
        });

        waitsFor(function () {
            return $('.g-file-list-entry').length === fileListLength - 1;
        }, 'file to be removed from the list');
    });

    it('Delete the item', function () {
        waitsFor(function () {
            return $('.g-item-actions-button:visible').length === 1;
        }, 'the item actions button to appear');

        runs(function () {
            $('.g-item-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-delete-item:visible').length === 1;
        }, 'the item delete action to appear');

        runs(function () {
            $('.g-delete-item').click();
        });

        girderTest.waitForDialog();

        waitsFor(function () {
            return $('#g-confirm-button:visible').length > 0;
        }, 'delete confirmation to appear');

        runs(function () {
            $('#g-confirm-button').click();
        });

        waitsFor(function () {
            return $('.g-item-list-container').length > 0;
        }, 'go back to the item list');

        girderTest.waitForLoad();

        runs(function () {
            expect($('.g-item-list-entry').text()).not.toContain('Test Item Name');
        });
    });
});
