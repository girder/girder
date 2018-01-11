girderTest.startApp();

describe('Test collection actions', function () {
    var privateCollectionFragment, privateFolderFragment;

    it('register a user (first is admin)',
        girderTest.createUser('admin',
            'admin@email.com',
            'Admin',
            'Admin',
            'adminpassword!'));

    it('go to collections page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button:visible').length > 0;
        }, 'navigate to collections page');

        runs(function () {
            expect($('.g-collection-list-entry').length).toBe(0);
        });
    });

    it('create a collection',
        girderTest.createCollection('collName0', 'coll Desc 0', 'Private'));

    it('make sure nFolder is fetch', function () {
        runs(function () {
            $('.g-collection-info-button').click();
        });

        waitsFor(function () {
            return $('#g-dialog-container:visible').length > 0;
        }, 'collection info dialog to appear');

        runs(function () {
            for (var i = 0; i < 4; i++) {
                if ($('.g-collection-info-line').eq(i).attr('property') === 'id') {
                    var id = $('.g-bold-part').eq(i).text();
                    var n = $('.g-bold-part').eq(i - 1).text();
                    console.log('ID ', id, ' - nFolder ', n);
                }
            }
        });

        runs(function () {
            $('.btn-default').click();
        });

        waitsFor(function () {
            return $('#g-dialog-container:visible').length === 0;
        }, 'collection info dialog to be closed');
    });

    it('go back to collections page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button:visible').length > 0;
        }, 'navigate to collections page');

        waitsFor(function () {
            return $('.g-collection-list-entry').length === 1;
        }, 'collection list to appear');

        runs(function () {
            expect($('.g-collection-list-entry').text()).toContain('collName0');
            expect($('.g-collection-subtitle').text()).toBe('Show description');
            expect($('.g-collection-description:visible').length).toBe(0);

            // Show description
            $('.g-show-description').click();
            expect($('.g-collection-subtitle').text()).toBe('Hide description');
            expect($('.g-collection-description:visible').length).toBe(1);
            expect($('.g-collection-description').text().trim()).toBe('coll Desc 0');

            // Hide description
            $('.g-show-description').click();
            expect($('.g-collection-subtitle').text()).toBe('Show description');
            expect($('.g-collection-description:visible').length).toBe(0);
        });
    });

    it('create another collection',
        girderTest.createCollection('collName1', 'coll Desc 1', 'Private'));

    it('change collection description', function () {
        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');

        runs(function () {
            $('.g-collection-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-edit-collection').is(':visible');
        }, 'edit collection menu item to appear');

        runs(function () {
            privateCollectionFragment = Backbone.history.fragment;
            $('.g-edit-collection').click();
        });
        girderTest.waitForDialog();

        waitsFor(function () {
            return $('#collection-description-write .g-markdown-text').is(':visible');
        }, 'description text area to appear');

        runs(function () {
            $('#collection-description-write .g-markdown-text').val('New Description');
            $('.g-save-collection').click();
        });

        waitsFor(function () {
            return $('.modal').data('bs.modal').isShown === false &&
                   $('#g-dialog-container:visible').length === 0;
        }, 'dialog to fully disappear');
        waitsFor(function () {
            return girder.rest.numberOutstandingRestRequests() === 0;
        }, 'dialog rest requests to finish');

        waitsFor(function () {
            return $('.g-collection-description').text().trim().match('New Description');
        }, 'description to be updated to new text');

        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');

        runs(function () {
            $('.g-collection-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-edit-collection').is(':visible');
        }, 'ensure edit collection menu item continues to appear');

        // save fragment of Private folder
        runs(function () {
            expect($('.g-collection-actions-button:visible').length).toBe(1);
            $('.g-folder-list-link:first').click();
        });

        waitsFor(function () {
            return $('.g-folder-metadata').is(':visible');
        }, 'ensure collection folder is displayed');

        runs(function () {
            // Collection actions should disappear once we navigate into subfolder
            expect($('.g-collection-actions-button:visible').length).toBe(0);
            privateFolderFragment = Backbone.history.fragment;
        });
    });

    it('test that login dialog appears when anonymous loads a private collection', function () {
        girderTest.waitForLoad();
        girderTest.anonymousLoadPage(true, privateCollectionFragment, true);
    });

    it('test that login dialog appears when anonymous loads a private folder in a private collection', function () {
        girderTest.waitForLoad();
        girderTest.anonymousLoadPage(false, privateFolderFragment, true);
    });

    it('make new collection public', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();

        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button:visible').length > 0;
        }, 'navigate to collections page');

        waitsFor(function () {
            return $('.g-collection-list-entry').length === 2;
        }, 'collection list to appear');

        runs(function () {
            $('.g-collection-link:last').click();
        });

        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');

        runs(function () {
            $('.g-collection-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-collection-access-control[role="menuitem"]:visible').length === 1;
        }, 'access control menu item to appear');

        runs(function () {
            $('.g-collection-access-control').click();
        });
        girderTest.waitForDialog();

        waitsFor(function () {
            return $('#g-dialog-container').hasClass('in') &&
                   $('#g-access-public:visible').is(':enabled');
        }, 'dialog and public access radio button to appear');

        runs(function () {
            $('#g-access-public').click();
        });

        waitsFor(function () {
            return $('.g-save-access-list:visible').is(':enabled') &&
                   $('.radio.g-selected').text().match('Public').length > 0;
        }, 'access save button to appear');

        runs(function () {
            $('.g-save-access-list').click();
        });

        girderTest.waitForLoad();

        waitsFor(function () {
            return !$('#g-dialog-container').hasClass('in');
        }, 'access dialog to be hidden');
    });

    it('logout and check for redirect to front page from collection page', function () {
        girderTest.logout()();

        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });

    it('test that login dialog does not appear when anonymous loads a public collection', function () {
        // despite its name, privateCollectionFragment now points to a public collection
        girderTest.anonymousLoadPage(false, privateCollectionFragment, false);
    });

    it('test that login dialog appears when anonymous loads a private folder in a public collection', function () {
        girderTest.anonymousLoadPage(false, privateFolderFragment, true);
    });

    it('go back to collections page again', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();

        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button').is(':enabled');
        }, 'navigate to collections page');

        waitsFor(function () {
            return $('.g-collection-list-entry').text().match('collName1').length > 0;
        }, 'new collection to appear');
    });

    it('logout to become anonymous, and check for redirect to front page from collections list page', function () {
        girderTest.logout()();

        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });

    it('check if public collection is viewable (and ensure private is not)', function () {
        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });

        waitsFor(function () {
            return $('li.active .g-page-number').text() === 'Page 1' &&
                   $('.g-collection-list-entry').length === 1;
        }, 'collection list page to reload');

        runs(function () {
            expect($('.g-collection-list-entry').text()).not.toContain('collName0');
        });

        waitsFor(function () {
            return $('.g-collection-list-entry').text().match('collName1') !== null;
        }, 'collName1 to appear');
    });

    it('log back in', girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));

    it('delete the collection', function () {
        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button').is(':enabled');
        }, 'navigate to collections page');

        waitsFor(function () {
            return $('.g-collection-list-entry').text().match('collName0').length > 0;
        }, 'new collection to appear');

        girderTest.waitForLoad();

        runs(function () {
            $('.g-collection-link:first').click();
        });

        waitsFor(function () {
            return $('.g-collection-actions-button').length > 0;
        }, 'collection view to load');

        waitsFor(function () {
            return $('.g-loading-block').length === 0;
        }, 'for all blocks to load');

        girderTest.waitForLoad();

        runs(function () {
            $('.g-collection-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-delete-collection:visible').length > 0;
        }, 'delete button to appear');

        runs(function () {
            $('.g-delete-collection').click();
        });

        waitsFor(function () {
            return $('#g-confirm-button:visible').length > 0;
        }, 'delete confirmation to appear');

        girderTest.waitForDialog();

        waitsFor(function () {
            $('#g-confirm-text').val('DELETE wrongName');
            return $('#g-confirm-text').val() === 'DELETE wrongName';
        }, 'enter the wrong message of delete confirmation');

        runs(function () {
            $('#g-confirm-button').click();
        });

        waitsFor(function () {
            return $('.g-msg-error').is(':visible');
        }, 'error message to be displayed');

        waitsFor(function () {
            $('#g-confirm-text').val('');
            return $('#g-confirm-text').val() === '';
        }, 'forget to enter the message of delete confirmation');

        runs(function () {
            $('#g-confirm-button').click();
        });

        waitsFor(function () {
            return $('.g-msg-error').is(':visible');
        }, 'error message to be displayed');

        waitsFor(function () {
            $('#g-confirm-text').val('DELETE collName0');
            return $('#g-confirm-text').val() === 'DELETE collName0';
        }, 'enter the right message of delete confirmation');

        runs(function () {
            $('#g-confirm-button').click();
        });

        waitsFor(function () {
            return $('.g-collection-list-header').length > 0;
        }, 'go back to the collections list');

        girderTest.waitForLoad();

        runs(function () {
            expect($('.g-collection-list-entry').text()).not.toContain('collName0');
            expect($('.g-collection-list-entry').length).toBe(1);
        });
    });
});
