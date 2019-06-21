/* global girderTest, describe, it, expect, runs, waitsFor, girder, beforeEach */

girderTest.importPlugin('terms');
girderTest.startApp();

describe('Create and log in to a user for testing', function () {
    it('create an admin user', girderTest.createUser('rocky', 'rocky@phila.pa.us', 'Robert', 'Balboa', 'adrian'));

    it('allow all users to create collections', function () {
        var settingSaved;
        runs(function () {
            settingSaved = false;
            girder.rest.restRequest({
                url: 'system/setting',
                method: 'PUT',
                data: {
                    key: 'core.collection_create_policy',
                    value: JSON.stringify({ groups: [], open: true, users: [] })
                }
            })
                .done(function () {
                    settingSaved = true;
                });
        });
        waitsFor(function () {
            return settingSaved;
        });
    });

    it('logout', girderTest.logout());

    it('create a collection admin user', girderTest.createUser('creed', 'creed@la.ca.us', 'Apollo', 'Creed', 'the1best'));
});

describe('Ensure that basic collections still work', function () {
    it('go to collections page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });
        waitsFor(function () {
            return $('.g-collection-create-button:visible').length > 0;
        });
        runs(function () {
            expect($('.g-collection-list-entry').length).toBe(0);
        });
    });

    it('create a basic collection', girderTest.createCollection('Basic Collection', 'Some description.', 'Basic Folder'));
});

describe('Navigate to a non-collection folder and item', function () {
    it('navigate to user folders page', function () {
        runs(function () {
            $('a.g-my-folders').click();
        });
        waitsFor(function () {
            return $('.g-user-header').length > 0 && $('.g-folder-list-entry').length > 0;
        });
    });

    it('navigate to the Public folder', function () {
        runs(function () {
            var folderLink = $('.g-folder-list-link:contains("Public")');
            expect(folderLink.length).toBe(1);
            folderLink.click();
        });
        waitsFor(function () {
            return $('.g-item-count-container:visible').length === 1;
        });
        girderTest.waitForLoad();
        runs(function () {
            expect($('.g-hierarchy-breadcrumb-bar>.breadcrumb>.active').text()).toBe('Public');
            var folderId = window.location.hash.split('/')[3];
            expect(folderId).toMatch(/[0-9a-f]{24}/);
            window.location.assign('#folder/' + folderId);
        });
        // after setting a window location, waitForLoad is insufficient, as the
        // page hasn't yet started making requests and it looks similar to
        // before the location change.  Wait for the user header to be hidden,
        // and then wait for load.
        waitsFor(function () {
            return $('.g-user-header').length === 0;
        }, 'the user header to go away');
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-item-count-container:visible').length === 1;
        });
    });

    it('create an item', function () {
        runs(function () {
            $('.g-create-item').click();
        });
        girderTest.waitForDialog();

        waitsFor(function () {
            return $('.modal-body input#g-name').length > 0;
        });
        runs(function () {
            $('#g-name').val('User Item');
            $('.g-save-item').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-item-list-link').length > 0;
        });
    });

    it('navigate to the new item', function () {
        runs(function () {
            var itemLink = $('.g-item-list-link:contains("User Item")');
            expect(itemLink.length).toBe(1);
            itemLink.click();
        });
        waitsFor(function () {
            return $('.g-item-header').length > 0;
        });
        runs(function () {
            expect($('.g-item-header .g-item-name').text()).toBe('User Item');
            termsItemId = window.location.hash.split('/')[1];
            expect(termsItemId).toMatch(/[0-9a-f]{24}/);
        });
    });
});

var termsCollectionId, termsFolderId, termsItemId;
describe('Create a collection with terms', function () {
    it('go to collections page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });
        waitsFor(function () {
            return $('.g-collection-create-button:visible').length > 0;
        });
    });

    it('open the create collection dialog', function () {
        waitsFor(function () {
            return $('.g-collection-create-button').is(':enabled');
        });
        runs(function () {
            $('.g-collection-create-button').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#collection-terms-write .g-markdown-text').is(':visible');
        });
    });

    it('fill and submit the create collection dialog', function () {
        runs(function () {
            $('#g-name').val('Terms Collection');
            $('#collection-description-write .g-markdown-text').val('Some other description.');
            $('#collection-terms-write .g-markdown-text').val('# Sample Terms of Use\n\n**\u00af\\\\\\_(\u30c4)\\_/\u00af**');
            $('.g-save-collection').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-collection-header').length > 0;
        });
        runs(function () {
            expect($('.g-collection-header .g-collection-name').text()).toBe('Terms Collection');
            termsCollectionId = window.location.hash.split('/')[1];
            expect(termsCollectionId).toMatch(/[0-9a-f]{24}/);
        });
    });

    it('make the collection public', function () {
        runs(function () {
            $('.g-edit-access').click();
        });
        girderTest.waitForDialog();
        runs(function () {
            $('#g-access-public').click();
            $('.g-save-access-list').click();
        });
        girderTest.waitForLoad();
    });

    it('check the collection info dialog', function () {
        runs(function () {
            $('.g-collection-info-button').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('.g-terms-info').length > 0;
        });
        runs(function () {
            expect($('.g-terms-info>h1').text()).toBe('Sample Terms of Use');
        });
        runs(function () {
            $('.modal-header .close').click();
        });
        girderTest.waitForLoad();
    });

    it('create a folder', function () {
        runs(function () {
            return $('.g-create-subfolder').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('.modal-body input#g-name').length > 0;
        });
        runs(function () {
            $('#g-name').val('Terms Folder');
            $('.g-save-folder').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-folder-list-link').length > 0;
        });
    });

    it('navigate to the new folder', function () {
        runs(function () {
            var folderLink = $('.g-folder-list-link:contains("Terms Folder")');
            expect(folderLink.length).toBe(1);
            folderLink.click();
        });
        waitsFor(function () {
            return $('.g-item-count-container:visible').length === 1;
        });
        runs(function () {
            expect($('.g-hierarchy-breadcrumb-bar>.breadcrumb>.active').text()).toBe('Terms Folder');
            termsFolderId = window.location.hash.split('/')[3];
            expect(termsFolderId).toMatch(/[0-9a-f]{24}/);
        });
    });

    it('create an item', function () {
        runs(function () {
            return $('.g-create-item').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('.modal-body input#g-name').length > 0;
        });
        runs(function () {
            $('#g-name').val('Terms Item');
            $('.g-save-item').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-item-list-link').length > 0;
        });
    });

    it('navigate to the new item', function () {
        runs(function () {
            var itemLink = $('.g-item-list-link:contains("Terms Item")');
            expect(itemLink.length).toBe(1);
            itemLink.click();
        });
        waitsFor(function () {
            return $('.g-item-header').length > 0;
        });
        runs(function () {
            expect($('.g-item-header .g-item-name').text()).toBe('Terms Item');
            termsItemId = window.location.hash.split('/')[1];
            expect(termsItemId).toMatch(/[0-9a-f]{24}/);
        });
    });
});

// TODO: rerun this whole suite while logged in
describe('Ensure that anonymous users are presented with terms', function () {
    beforeEach(function () {
        window.localStorage.clear();
    });

    it('logout', girderTest.logout());

    it('navigate to the collection page, rejecting terms', function () {
        runs(function () {
            window.location.assign('#collection/' + termsCollectionId);
        });
        waitsFor(function () {
            return $('.g-terms-container').length > 0;
        });
        runs(function () {
            expect($('.g-terms-info>h1').text()).toBe('Sample Terms of Use');
            $('#g-terms-reject').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-frontpage-header').length > 0;
        });
    });

    it('navigate to the collection page', function () {
        runs(function () {
            window.location.assign('#collection/' + termsCollectionId);
        });
        waitsFor(function () {
            return $('.g-terms-container').length > 0;
        });
        runs(function () {
            expect($('.g-terms-info>h1').text()).toBe('Sample Terms of Use');
            $('#g-terms-accept').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-collection-header').length > 0;
        });
        runs(function () {
            expect($('.g-collection-header .g-collection-name').text()).toBe('Terms Collection');
        });
    });

    it('navigate to the folder page', function () {
        runs(function () {
            window.location.assign('#folder/' + termsFolderId);
        });
        waitsFor(function () {
            return $('.g-terms-container').length > 0;
        });
        runs(function () {
            expect($('.g-terms-info>h1').text()).toBe('Sample Terms of Use');
            $('#g-terms-accept').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-item-count-container:visible').length === 1;
        });
        runs(function () {
            expect($('.g-hierarchy-breadcrumb-bar>.breadcrumb>.active').text()).toBe('Terms Folder');
        });
    });

    it('navigate to the item page', function () {
        runs(function () {
            window.location.assign('#item/' + termsItemId);
        });
        waitsFor(function () {
            return $('.g-terms-container').length > 0;
        });
        runs(function () {
            expect($('.g-terms-info>h1').text()).toBe('Sample Terms of Use');
            $('#g-terms-accept').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-item-header').length > 0;
        });
        runs(function () {
            expect($('.g-item-header .g-item-name').text()).toBe('Terms Item');
        });
    });
});

// TODO: edit the collection with WRITE permissions only

describe('Change the terms', function () {
    it('login as collection admin', girderTest.login('creed', 'Apollo', 'Creed', 'the1best'));

    it('navigate to the terms collection', function () {
        runs(function () {
            $('a.g-nav-link[g-target="collections"]').click();
        });
        waitsFor(function () {
            return $('.g-collection-list-entry').length > 0;
        });
        girderTest.waitForLoad();
        runs(function () {
            $('.g-collection-link:contains("Terms Collection")').click();
        });
        waitsFor(function () {
            return $('.g-collection-header').length > 0;
        });
        girderTest.waitForLoad();
    });

    it('edit the collection terms', function () {
        runs(function () {
            $('.g-edit-folder').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#collection-terms-write .g-markdown-text').is(':visible');
        });
        runs(function () {
            $('#collection-terms-write .g-markdown-text').val('# New Terms of Use\n\nThese have changed.');
            $('.g-save-collection').click();
        });
        girderTest.waitForLoad();
        runs(function () {
            expect($('.g-collection-header .g-collection-name').text()).toBe('Terms Collection');
        });
    });
});

describe('Ensure that anonymous users need to re-accept the updated terms', function () {
    it('logout', girderTest.logout());

    it('ensure that the old terms acceptance is still stored', function () {
        expect(window.localStorage.length).toBe(1);
    });

    it('navigate to the collection page', function () {
        runs(function () {
            window.location.assign('#collection/' + termsCollectionId);
        });
        waitsFor(function () {
            return $('.g-terms-container').length > 0;
        });
        runs(function () {
            expect($('.g-terms-info>h1').text()).toBe('New Terms of Use');
            $('#g-terms-accept').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-collection-header').length > 0;
        });
        runs(function () {
            expect($('.g-collection-header .g-collection-name').text()).toBe('Terms Collection');
        });
    });
});
