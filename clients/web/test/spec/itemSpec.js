/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
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

function _editMetadata(origKey, key, value, action, errorMessage)
/* Add metadata and check that the value is actually set for the item.
 * :param origKey: null to create a new metadata item.  Otherwise, edit the
 *                 metadata item with this key.
 * :param key: key text.
 * :param value: value text.  If this appears to be a JSON string, the metadata
 *               should be stored as a JSON object.
 * :param action: one of 'save', 'cance', or 'delete'.  'delete' can't be used
 *                with new items.  Default is 'save'.
 * :param errorMessage: if present, expect an information message with regex.
 */
{
    var expectedNum, elem;

    if (origKey === null)
    {
        waitsFor(function () {
            return $('.g-widget-metadata-add-button:visible').length === 1;
        }, 'the add metadata button to appear');
        runs(function () {
            expectedNum = $(".g-widget-metadata-row").length;
            $('.g-widget-metadata-add-button:visible').click();
        });
    }
    else
    {
        runs(function () {
            elem = $('.g-widget-metadata-key:contains("'+origKey+'")').closest('.g-widget-metadata-row');
            expect(elem.length).toBe(1);
            expect($('.g-widget-metadata-edit-button', elem).length).toBe(1);
            expectedNum = $(".g-widget-metadata-row").length;
            $('.g-widget-metadata-edit-button', elem).click();
        });
    }
    waitsFor(function () {
        return $('input.g-widget-metadata-key-input').length === 1 &&
               $('textarea.g-widget-metadata-value-input').length === 1;
    }, 'the add metadata input fields to appear');
    runs(function () {
        if (!elem) {
            elem = $('input.g-widget-metadata-key-input').closest('.g-widget-metadata-row');
        }
        if (key !== null) {
            $('input.g-widget-metadata-key-input', elem).val(key);
        } else {
            key = $('input.g-widget-metadata-key-input', elem).val();
        }
        if (value !== null) {
            $('textarea.g-widget-metadata-value-input', elem).val(value);
        } else {
            value = $('textarea.g-widget-metadata-value-input', elem).val();
        }
    });
    if (errorMessage) {
        runs(function () {
            $('.g-widget-metadata-save-button').click();
        });
        waitsFor(function () {
            return $('.alert').text().match(errorMessage);
        }, 'alert with "'+errorMessage+'" to appear');
    }
    switch (action)
    {
        case 'cancel':
            runs(function () {
                $('.g-widget-metadata-cancel-button').click();
            });
            break;
        case 'delete':
            runs(function () {
                $('.g-widget-metadata-delete-button').click();
            });
            girderTest.waitForDialog();
            waitsFor(function () {
                return $('#g-confirm-button:visible').length > 0;
            }, 'delete confirmation to appear');
            runs(function () {
                $('#g-confirm-button').click();
                expectedNum -= 1;
            });
            girderTest.waitForLoad();
            break;
        default:
            action = 'save';
            runs(function () {
                $('.g-widget-metadata-save-button').click();
                if (origKey === null) {
                    expectedNum += 1;
                }
            });
            break;
    }
    waitsFor(function () {
        return $('input.g-widget-metadata-key-input').length === 0 &&
               $('textarea.g-widget-metadata-value-input').length === 0;
    }, 'edit fields to disappear');
    waitsFor(function () {
        return $(".g-widget-metadata-row").length == expectedNum;
    }, 'the correct number of items to be listed');
    runs(function () {
        expect($(".g-widget-metadata-row").length).toBe(expectedNum);
        if (action === 'save') {
            expect(elem.text()).toBe(key+value);
        }
    });
}

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

    it('Open edit dialog and check url state', function () {
        _editItem('a.btn-default', 'Cancel');
    });

    it('Add, edit, and delete metadata for the item', function () {
        _editMetadata(null, 'simple_key', 'simple_value');
        _editMetadata(null, 'simple_key', 'duplicate_key_should_fail', 'cancel', /.*simple_key is already a metadata key/);
        _editMetadata(null, '', 'no_key', 'cancel', /.*A key is required for all metadata/);
        _editMetadata(null, 'cancel_me', 'this will be cancelled', 'cancel');
        _editMetadata(null, 'long_key', 'long_value'+new Array(2048).join('-'));
        _editMetadata(null, 'json_key', JSON.stringify({'sample_json': 'value'}));
        _editMetadata('simple_key', null, 'new_value', 'cancel');
        _editMetadata('long_key', 'simple_key', 'new_value', 'cancel', /.*simple_key is already a metadata key/);
        _editMetadata('simple_key', null, 'new_value');
        _editMetadata('simple_key', null, null, 'delete');
        _editMetadata('json_key', 'json_rename', null);
    });

    it('Open edit dialog and save the item', function () {
        _editItem('button.g-save-item', 'Save');
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
