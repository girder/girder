/**
 * Start the girder backbone app.
 */
/* globals waitsFor, runs, girderTest, expect, describe, it */

$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({
        el: 'body',
        parentView: null
    });
    app = app;
    girder.events.trigger('g:appload.after');
});

/* Show the folder edit dialog and click a button.
 * :param button: the jquery selector for the button.
 * :param buttonText: the expected text of the button.
 * :param testValidation: if true, try to clear the name and select submit.
 */
function _editFolder(button, buttonText, testValidation) {
    var oldval;

    waitsFor(function () {
        return $('.g-folder-actions-button:visible').length === 1;
    }, 'the folder actions button to appear');

    runs(function () {
        $('.g-folder-actions-button').click();
    });

    waitsFor(function () {
        return $('.g-edit-folder:visible').length === 1;
    }, 'the folder edit action to appear');

    runs(function () {
        $('.g-edit-folder').click();
    });

    waitsFor(function () {
        return Backbone.history.fragment.slice(-18) === '?dialog=folderedit';
    }, 'the url state to change');
    girderTest.waitForDialog();

    waitsFor(function () {
        return $('#g-name').val() !== '' && $(button).text() === buttonText;
    }, 'the dialog to be populated and the button to appear');

    if (testValidation) {
        runs(function () {
            expect($('.g-upload-footer').length).toBe(1);
            oldval = $('#g-name').val();
            $('#g-name').val('');
            $('.g-save-folder').click();
        });
        waitsFor(function () {
            return $('.g-validation-failed-message').text() === 'Folder name must not be empty.';
        }, 'the validation to fail.');

        runs(function () {
            $('#g-name').val(oldval);
            girderTest.sendFile('clients/web/test/testFile.txt',
                                '.g-markdown-drop-zone .g-file-input');
        });

        waitsFor(function () {
            return $('#g-alerts-container .alert-danger').text().indexOf(
                'Only files with the following extensions are allowed: ' +
                'png, jpg, jpeg, gif.') !== -1;
        }, 'allowed extension message to show up');

        runs(function () {
            girderTest.sendFile('clients/web/test/fake.jpg',
                                '.g-markdown-drop-zone .g-file-input');
        });

        waitsFor(function () {
            return $('#g-dialog-container .g-markdown-text').val().indexOf(
                '![fake.jpg](' + girder.apiRoot) !== -1;
        }, 'image to be attached to the markdown');

        runs(function () {
            expect($('#g-dialog-container .g-markdown-text').val()).toMatch(
                /!\[fake\.jpg]\(.*\/download\)/);
            $('#g-dialog-container .g-preview-link').click();
        });

        waitsFor(function () {
            return $('.g-markdown-preview img').length === 1;
        }, 'preview to show the uploaded image');

        /* Test drag-and-drop.  Don't bother actually transferring a file --
         * that functionality is already tested. */
        runs(function () {
            $('#g-dialog-container .g-write-link').click();
        });
        waitsFor(function () {
            return $('.g-markdown-text:visible').length > 0;
        }, 'the write tab to be visible');

        runs(function () {
            girderTest.testUploadDropAction(
                10 * 1024 * 1024 + 1, 1, '.g-markdown-drop-zone',
                '.g-markdown-text.dragover');
            waitsFor(function () {
                return $('#g-alerts-container .alert-danger').text().indexOf(
                    'That file is too large.') !== -1;
            }, 'file too large message to show up');
        });
    }

    runs(function () {
        $(button).click();
    });
    girderTest.waitForLoad();
}

describe('Test folder creation, editing, and deletion', function () {
    it('register a user',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));

    it('go to users page', girderTest.goToUsersPage());

    it('view the users on the user page and click on one', function () {
        runs(function () {
            expect($('.g-user-list-entry').length).toBe(1);
        });

        runs(function () {
            $('a.g-user-link:contains("Admin")').click();
        });

        waitsFor(function () {
            return $('.g-user-name').text() === 'Admin Admin';
        }, 'user page to appear');

        // check for actions menu
        runs(function () {
            expect($('button:contains("Actions")').length).toBe(1);
        });
    });

    it('test that anonymous loading the private folder of the user prompts a login dialog', function () {
        waitsFor(function () {
            return $('a.g-folder-list-link:contains(Private):visible').length === 1;
        }, 'the private folder to be clickable');

        runs(function () {
            $('a.g-folder-list-link:contains(Private)').click();
        });

        waitsFor(function () {
            return Backbone.history.fragment.search('folder') > -1;
        }, 'the url state to change');

        runs(function () {
            var privateFolderFragment = Backbone.history.fragment;
            girderTest.anonymousLoadPage(true, privateFolderFragment, true, girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
        });

        // get back to where you once belonged, the User page, so that testing may continue
        girderTest.goToUsersPage()();

        runs(function () {
            expect($('.g-user-list-entry').length).toBe(1);
        });

        runs(function () {
            $('a.g-user-link:contains("Admin")').click();
        });

        waitsFor(function () {
            return $('.g-user-name').text() === 'Admin Admin';
        }, 'user page to appear');

        // check for actions menu
        runs(function () {
            expect($('button:contains("Actions")').length).toBe(1);
        });
    });

    it('create a subfolder in the public folder of the user', function () {

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
            return $('a.g-create-subfolder:visible').length === 1;
        }, 'create folder option is clickable');

        runs(function () {
            $('.g-create-subfolder:visible').click();
        });

        girderTest.waitForDialog();
        waitsFor(function () {
            return Backbone.history.fragment.slice(-20) === '?dialog=foldercreate';
        }, 'the url state to change');

        waitsFor(function () {
            return $('a.btn-default:visible').text() === 'Cancel';
        }, 'the cancel button of the folder create dialog to appear');

        runs(function () {
            expect($('.g-upload-footer').length).toBe(0);
            $('.g-save-folder').click();
        });
        waitsFor(function () {
            return $('.g-validation-failed-message').text() === 'Folder name must not be empty.';
        }, 'the validation to fail.');

        runs(function () {
            $('#g-name').val('Test Folder Name');
            $('.g-description-editor-container .g-markdown-text').val(
                '## Test Description');
            $('.g-description-editor-container .g-preview-link').click();
        });

        waitsFor(function () {
            return $('.g-markdown-preview h2:contains("Test Description")').length === 1;
        }, 'markdown preview to show up correctly');

        runs(function () {
            $('.g-save-folder').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-folder-list-link:contains("Test Folder Name")').length === 1;
        }, 'the new folder to appear in the list');

        runs(function () {
            $('.g-folder-info-button').click();
        });
        girderTest.waitForDialog();

        runs(function () {
            expect($('.g-folder-info-line[property="nItems"]').text()).toBe(
                'Contains 0 items totaling 0 B');
            expect($('.g-folder-info-line[property="nFolders"]').text()).toBe(
                'Contains 1 subfolders');
            expect($('.g-folder-info-line[property="created"]').text()).toContain(
                'Created ');
            expect($('.g-folder-description').length).toBe(0);
            $('.modal-footer a[data-dismiss="modal"]').click();
        });
        girderTest.waitForLoad();

        runs(function () {
            $('a.g-folder-list-link:contains("Test Folder Name")').click();
        });

        waitsFor(function () {
            return $('.breadcrumb .active:contains("Test Folder Name")').length === 1;
        }, 'the folder page to load');
        runs(function () {
            expect($('.breadcrumb .active').text()).toBe('Test Folder Name');
        });
    });

    it('Open edit dialog and check url state', function () {
        _editFolder('a.btn-default', 'Cancel');
    });

    it('Add, edit, and delete metadata for the folder', girderTest.testMetadata());

    it('Open edit dialog and save the folder', function () {
        _editFolder('button.g-save-folder', 'Save', true);
    });

    it('Test folder view and navigation', function () {
        waitsFor(function () {
            return $('.g-folder-actions-button:visible').length === 1;
        }, 'folder actions to be available');

        runs(function () {
            $('.g-folder-actions-button:visible').click();
        });

        waitsFor(function () {
            return $('a.g-create-item:visible').length === 1;
        }, 'create item option is clickable');

        runs(function () {
            $('.g-create-item:visible').click();
        });

        girderTest.waitForDialog();
        waitsFor(function () {
            return $('a.btn-default:visible').text() === 'Cancel';
        }, 'the cancel button of the item create dialog to appear');

        runs(function () {
            $('#g-name').val('Test Item Name');
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
            return $('.g-item-name:contains(Test Item Name)').length &&
                   $('a.g-item-breadcrumb-link:last').length > 0;
        }, 'the item page to load');
        girderTest.waitForLoad();

        runs(function () {
            $('a.g-item-breadcrumb-link:last').click();
        });

        waitsFor(function () {
            return $('a.g-breadcrumb-link').length === 2;
        }, 'the folder page to load');
        girderTest.waitForLoad();

        runs(function () {
            expect($('.g-widget-metadata-row').length).toNotBe(0);
            $('i.icon-level-up').click();
        });

        waitsFor(function () {
            return $('a.g-breadcrumb-link').length === 1;
        }, 'the folder page to load');
        girderTest.waitForLoad();

        runs(function () {
            /* This folder shouldn't show any metadata */
            expect($('.g-widget-metadata-row').length).toBe(0);
            $('a.g-breadcrumb-link').click();
        });

        waitsFor(function () {
            return $('a.g-breadcrumb-link').length === 0;
        }, 'the user page to load');
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-folder-list-link:contains(Public):visible').length === 1;
        }, 'the public folder to be clickable');

        runs(function () {
            $('a.g-folder-list-link:contains(Public)').click();
        });

        waitsFor(function () {
            return $('a.g-folder-list-link:contains(Test Folder Name):visible').length === 1;
        }, 'the public folder to be clickable');

        runs(function () {
            $('a.g-folder-list-link:contains(Test Folder Name)').click();
        });
        waitsFor(function () {
            return $('a.g-breadcrumb-link').length === 2;
        }, 'the folder page to load');
        girderTest.waitForLoad();
    });

    it('Test folder access control', function () {
        girderTest.folderAccessControl('public', 'private');
    });

    it('Delete the folder', function () {
        waitsFor(function () {
            return $('.g-folder-actions-button:visible').length === 1;
        }, 'the folder actions button to appear');

        runs(function () {
            $('.g-folder-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-delete-folder:visible').length === 1;
        }, 'the folder delete action to appear');

        runs(function () {
            $('.g-delete-folder').click();
        });

        girderTest.waitForDialog();

        waitsFor(function () {
            return $('#g-confirm-button:visible').length > 0;
        }, 'delete confirmation to appear');

        runs(function () {
            $('#g-confirm-button').click();
        });

        waitsFor(function () {
            return $('.g-empty-parent-message:visible').length === 1 &&
                   $('.g-folder-actions-button:visible').length === 1;
        }, 'An empty folder to be shown');
        girderTest.waitForLoad();

        runs(function () {
            expect($('.breadcrumb .active').text()).toBe('Public');
        });
    });
});
