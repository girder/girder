/* globals girderTest, describe, it, runs, expect, waitsFor */

girderTest.addCoveredScripts([
    // '/plugins/geospatial/web_client/models/ItemModel.js',
    // '/plugins/geospatial/web_client/views/GeospatialItemWidget.js',
    // '/plugins/geospatial/web_client/views/ItemView.js',
    // '/plugins/geospatial/web_client/main.js'
]);
girderTest.addScripts([
    '/static/built/plugins/geospatial/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    describe('a test for the geospatial plugin', function () {
        it('creates the admin user', girderTest.createUser('geospatial',
                                                           'geospatial@girder.org',
                                                           'Geospatial', 'Plugin',
                                                           'fuprEsuxAth2S7ac'));

        it('creates an item and displays the geospatial info widget', function () {
            waitsFor(function () {
                return $('a.g-my-folders').length > 0;
            }, 'my folders link to load');
            runs(function () {
                $('a.g-my-folders').click();
            });
            waitsFor(function () {
                return $('a.g-folder-list-link:contains(Public)').length > 0;
            }, 'the folders list to load');
            runs(function () {
                $('a.g-folder-list-link:contains(Public)').click();
            });
            waitsFor(function () {
                return $('button.g-folder-actions-button:visible').length === 1;
            }, 'folder actions button to be visible');
            runs(function () {
                $('button.g-folder-actions-button:visible').click();
            });
            waitsFor(function () {
                return $('a.g-create-item:visible').length === 1;
            }, 'create item here link to be visible');
            runs(function () {
                $('a.g-create-item:visible').click();
            });
            waitsFor(function () {
                return Backbone.history.fragment.slice(-18) === '?dialog=itemcreate';
            }, 'the URL state to change');
            waitsFor(function () {
                return $('button.g-save-item:visible').text() === 'Create';
            }, 'the create item dialog to appear');
            runs(function () {
                $('input#g-name').val('Geospatial Item');
                $('button.g-save-item').click();
            });
            waitsFor(function () {
                return $('a.g-item-list-link:contains(Geospatial Item)').length === 1;
            }, 'the created item to appear in the folders list');
            runs(function () {
                $('a.g-item-list-link:contains(Geospatial Item)').click();
            });
            waitsFor(function () {
                return $('.g-item-name:contains(Geospatial Item)').length === 1;
            }, 'the item page to load');
            runs(function () {
                expect($('.g-item-geospatial').length > 0).toBe(true);
            });
        });
    });
});
