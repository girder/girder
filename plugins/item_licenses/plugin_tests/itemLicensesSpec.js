girderTest.importPlugin('item_licenses');
girderTest.startApp();

describe('item_licenses plugin test', function () {
    it('registers admin user',
        girderTest.createUser('admin',
            'admin@girder.test',
            'Admin',
            'User',
            'CxV`%EOsq9'));

    it('logs out', girderTest.logout());

    it('registers normal user',
        girderTest.createUser('user',
            'user@girder.test',
            'Normal',
            'User',
            'a*z/Swb?td'));

    it('creates an item with a license', function () {
        waitsFor(function () {
            return $('a.g-my-folders').length > 0;
        }, 'my folders link to load');
        runs(function () {
            $('a.g-my-folders').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-folder-list-link:contains(Public)').length > 0;
        }, 'the folders list to load');
        runs(function () {
            $('a.g-folder-list-link:contains(Public)').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('button.g-folder-actions-button:visible').length === 1;
        }, 'folder actions button to be visible');
        runs(function () {
            $('button.g-folder-actions-button:visible').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-create-item:visible').length === 1;
        }, 'create item here link to be visible');
        runs(function () {
            $('a.g-create-item:visible').trigger('click');
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-18) === '?dialog=itemcreate';
        }, 'the URL state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('button.g-save-item:visible').text() === 'Create';
        }, 'the create item dialog to appear');
        runs(function () {
            // Should list groups of licenses, plus "Unspecified" in dropdown
            expect($('#g-license optgroup').length).toBe(2);
            expect($('#g-license option').length).toBe(22);

            // "Unspecified" license should be selected by default (value is
            // empty string)
            expect($('#g-license').val()).toBe('');

            // Set item info and save
            $('input#g-name').val('Test Item');
            $('#g-license').val('The MIT License (MIT)');
            $('button.g-save-item').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-item-list-link:contains(Test Item)').length === 1;
        }, 'the created item to appear in the items list');
        runs(function () {
            $('a.g-item-list-link:contains(Test Item)').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-item-name').length === 1 && $('.g-item-license').length === 1;
        }, 'the item page and license field to load');
        girderTest.waitForLoad();

        runs(function () {
            // Item info should show license
            expect($('.g-item-license').length).toBe(1);
            expect($('.g-item-license').text()).toContain('The MIT License (MIT)');
        });
    });

    it('edits an item\'s license', function () {
        waitsFor(function () {
            return $('.g-item-actions-button:visible').length === 1;
        }, 'the item actions button to appear');
        runs(function () {
            $('.g-item-actions-button').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-edit-item:visible').length === 1;
        }, 'the item edit action to appear');
        runs(function () {
            $('.g-edit-item').trigger('click');
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-16) === '?dialog=itemedit';
        }, 'the url state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#g-name').val() !== '' && $('button.g-save-item:visible').text() === 'Save';
        }, 'the dialog to be populated');

        runs(function () {
            // Should list groups of licenses, plus "Unspecified" in dropdown
            expect($('#g-license optgroup').length).toBe(2);
            expect($('#g-license option').length).toBe(22);

            // The item's license should be selected by default
            expect($('#g-license').val()).toBe('The MIT License (MIT)');

            // Change the item's license
            $('#g-license').val('Apache License 2');
            $('button.g-save-item').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-item-name').length === 1 && $('.g-item-license').length === 1;
        }, 'the item page and license field to load');
        girderTest.waitForLoad();
        runs(function () {
            // Item info should show license
            expect($('.g-item-license').length).toBe(1);
            expect($('.g-item-license').text()).toContain('Apache License 2');
        });
    });

    it('verifies upload into an item dialog doesn\'t show license selection widget', function () {
        waitsFor(function () {
            return $('.g-upload-into-item:visible').length === 1;
        }, 'the upload into item action to appear');
        runs(function () {
            $('.g-upload-into-item').trigger('click');
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-14) === '?dialog=upload';
        }, 'the url state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('.g-start-upload:visible').text().indexOf('Start Upload') !== -1;
        }, 'the start upload button to appear');
        runs(function () {
            // Should not show license selection widget
            expect($('#g-license').length).toBe(0);
        });

        // Close dialog and return to Public folder listing
        waitsFor(function () {
            return $('button.close:visible').length === 1;
        }, 'the dialog close button to appear');
        runs(function () {
            $('button.close').trigger('click');
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('a.g-item-breadcrumb-link:contains(Public):visible').length === 1;
        }, 'the breadcrumb link to the public folder to appear');
        runs(function () {
            $('a.g-item-breadcrumb-link:contains(Public)').trigger('click');
        });
        girderTest.waitForLoad();
    });

    it('uploads an item, specifying a license', function () {
        waitsFor(function () {
            return $('.g-upload-here-button:visible').length === 1;
        }, 'the upload here button to appear');
        runs(function () {
            $('.g-upload-here-button').trigger('click');
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-14) === '?dialog=upload';
        }, 'the url state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('.g-start-upload:visible').text().indexOf('Start Upload') !== -1;
        }, 'the start upload button to appear');
        runs(function () {
            // Should show license selection widget
            expect($('#g-license').length).toBe(1);

            // Select a license
            $('#g-license').val('Apache License 2');
        });

        // Upload file
        // XXX: add support to test uploading multiple files
        runs(function () {
            girderTest._prepareTestUpload();
            girderTest._uploadDataExtra = 0;
            girderTest.sendFile('girder/web_client/test/testFile.txt');
        });
        waitsFor(function () {
            return $('.g-overall-progress-message i.icon-ok').length > 0;
        }, 'the filesChanged event to happen');
        runs(function () {
            $('#g-files').parent().addClass('hide');
            $('.g-start-upload').trigger('click');
        });
        waitsFor(function () {
            return $('.modal-content:visible').length === 0 &&
                   $('.g-item-list-entry').length === 2;
        }, 'the upload to finish');
        girderTest.waitForLoad();

        // Verify license of uploaded file
        waitsFor(function () {
            return $('a.g-item-list-link:contains(testFile.txt)').length === 1;
        }, 'the uploaded file to appear in the items list');
        runs(function () {
            $('a.g-item-list-link:contains(testFile.txt)').trigger('click');
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-item-name').length === 1 && $('.g-item-license').length === 1;
        }, 'the item page and license field to load');
        girderTest.waitForLoad();
        runs(function () {
            expect($('.g-item-name').text()).toBe('testFile.txt');
            expect($('.g-item-license').length).toBe(1);
            expect($('.g-item-license').text()).toContain('Apache License 2');
        });

        // Return to Public folder listing
        waitsFor(function () {
            return $('a.g-item-breadcrumb-link:contains(Public):visible').length === 1;
        }, 'the breadcrumb link to the public folder to appear');
        runs(function () {
            $('a.g-item-breadcrumb-link:contains(Public)').trigger('click');
        });
        girderTest.waitForLoad();
    });

    it('creates an item with an unspecified license', function () {
        waitsFor(function () {
            return $('button.g-folder-actions-button:visible').length === 1;
        }, 'folder actions button to be visible');
        runs(function () {
            $('button.g-folder-actions-button:visible').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-create-item:visible').length === 1;
        }, 'create item here link to be visible');
        runs(function () {
            $('a.g-create-item:visible').trigger('click');
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-18) === '?dialog=itemcreate';
        }, 'the URL state to change');
        waitsFor(function () {
            return $('button.g-save-item:visible').text() === 'Create';
        }, 'the create item dialog to appear');
        girderTest.waitForDialog();
        runs(function () {
            // Should list groups of licenses, plus "Unspecified" in dropdown
            expect($('#g-license optgroup').length).toBe(2);
            expect($('#g-license option').length).toBe(22);

            // Set item info and save
            $('input#g-name').val('Test Item 2');
            $('#g-license').val('');
            $('button.g-save-item').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('a.g-item-list-link:contains(Test Item 2)').length === 1;
        }, 'the created item to appear in the items list');
        runs(function () {
            $('a.g-item-list-link:contains(Test Item 2)').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-item-name').length === 1 && $('.g-item-license').length === 1;
        }, 'the item page and license field to load');
        girderTest.waitForLoad();

        runs(function () {
            // Item info should show that license is unspecified
            expect($('.g-item-license').length).toBe(1);
            expect($('.g-item-license').text()).toContain('Unspecified');
        });
    });

    it('edits an item that has an unspecified license', function () {
        waitsFor(function () {
            return $('.g-item-actions-button:visible').length === 1;
        }, 'the item actions button to appear');
        runs(function () {
            $('.g-item-actions-button').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-edit-item:visible').length === 1;
        }, 'the item edit action to appear');
        runs(function () {
            $('.g-edit-item').trigger('click');
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-16) === '?dialog=itemedit';
        }, 'the url state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#g-name').val() !== '';
        }, 'the dialog to be populated');
        waitsFor(function () {
            return $('button.g-save-item:visible').text() === 'Save';
        }, 'the edit item dialog to appear');
        runs(function () {
            // Should list groups of licenses, plus "Unspecified" in dropdown
            expect($('#g-license optgroup').length).toBe(2);
            expect($('#g-license option').length).toBe(22);

            // The unspecified license should be selected by default
            expect($('#g-license').val()).toBe('');

            // Change the item's license
            $('#g-license').val('The MIT License (MIT)');
            $('button.g-save-item').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-item-name').length === 1 && $('.g-item-license').length === 1;
        }, 'the item page and license field to load');
        girderTest.waitForLoad();
        runs(function () {
            // Item info should show license
            expect($('.g-item-license').length).toBe(1);
            expect($('.g-item-license').text()).toContain('The MIT License (MIT)');
        });
    });

    it('edits an item to have an unspecified license', function () {
        waitsFor(function () {
            return $('.g-item-actions-button:visible').length === 1;
        }, 'the item actions button to appear');
        runs(function () {
            $('.g-item-actions-button').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-edit-item:visible').length === 1;
        }, 'the item edit action to appear');
        runs(function () {
            $('.g-edit-item').trigger('click');
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-16) === '?dialog=itemedit';
        }, 'the url state to change');
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#g-name').val() !== '';
        }, 'the dialog to be populated');
        waitsFor(function () {
            return $('button.g-save-item:visible').text() === 'Save';
        }, 'the edit item dialog to appear');
        runs(function () {
            // Should list groups of licenses, plus "Unspecified" in dropdown
            expect($('#g-license optgroup').length).toBe(2);
            expect($('#g-license option').length).toBe(22);

            // The item's license should be selected by default
            expect($('#g-license').val()).toBe('The MIT License (MIT)');

            // Change the item's license
            $('#g-license').val('');
            $('button.g-save-item').trigger('click');
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-item-name').length === 1 && $('.g-item-license').length === 1;
        }, 'the item page and license field to load');
        girderTest.waitForLoad();
        runs(function () {
            // Item info should show that license is unspecified
            expect($('.g-item-license').length).toBe(1);
            expect($('.g-item-license').text()).toContain('Unspecified');
        });
    });
});
