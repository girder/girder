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

function _editFolder(button, buttonText, testValidation)
/* Show the folder edit dialog and click a button.
 * :param button: the jquery selector for the button.
 * :param buttonText: the expected text of the button.
 * :param testValidation: if true, try to clear the name and select submit.
 */
{
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
        return $('#g-name').val() !== '';
    }, 'the dialog to be populated');

    waitsFor(function () {
        return $(button).text() === buttonText;
    }, 'the button to appear');

    if (testValidation) {
        runs(function () {
            oldval = $('#g-name').val();
            $('#g-name').val('');
            $('.g-save-folder').click();
        });
        waitsFor(function () {
            return $('.g-validation-failed-message').text() === 'Folder name must not be empty.';
        }, 'the validation to fail.');
        runs(function () {
            $('#g-name').val(oldval);
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
            $("a.g-user-link:contains('Admin')").click();
        });

        waitsFor(function () {
            return $('.g-user-name').text() === 'Admin Admin';
        }, 'user page to appear');

        // check for actions menu
        runs(function () {
            expect($("button:contains('Actions')").length).toBe(1);
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
            $('.g-save-folder').click();
        });
        waitsFor(function () {
            return $('.g-validation-failed-message').text() === 'Folder name must not be empty.';
        }, 'the validation to fail.');

        runs(function () {
            $('#g-name').val('Test Folder Name');
            $('#g-description').val('Test Folder Description');
            $('.g-save-folder').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-folder-list-link:contains("Test Folder Name")').length === 1;
        }, 'the new folder to appear in the list');

        runs(function () {
            $('a.g-folder-list-link:contains("Test Folder Name")').click();
        });

        waitsFor(function () {
            return $('.breadcrumb .active:contains("Test Folder Name")').length === 1;
        }, 'the folder page to load');
        runs(function () {
            expect($('.breadcrumb .active').text()).toBe("Test Folder Name");
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
            expect($(".g-widget-metadata-row").length).toNotBe(0);
            $('i.icon-level-up').click();
        });

        waitsFor(function () {
            return $('a.g-breadcrumb-link').length === 1;
        }, 'the folder page to load');
        girderTest.waitForLoad();

        runs(function () {
            /* This folder shouldn't show any metadata */
            expect($(".g-widget-metadata-row").length).toBe(0);
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
            expect($('.breadcrumb .active').text()).toBe("Public");
        });
    });
});
