/* globals girderTest, describe, it, runs, expect, waitsFor */

girderTest.addCoveredScripts([
    // '/plugins/hashsum_download/web_client/views/FileInfoWidget.js',
    // '/plugins/hashsum_download/web_client/main.js'
]);
girderTest.addScripts([
    '/static/built/plugins/hashsum_download/plugin.min.js'
]);

girder.events.trigger('g:appload.before');
var app = new girder.views.App({
    el: 'body',
    parentView: null
});
girder.events.trigger('g:appload.after');

$(function () {
    describe('Unit test the file view augmentation', function () {
        var file;
        var sha512 = 'd9f804f8f7caceec12a1207c16c6b70cb1dbfd8ea8f48a36168c98898c' +
            '1f138a11e9d1b40769d3c112afb099c6be5d57fc1ee8cf353df91ca0d3cf5524ddb047';

        it('Create a file and its info dialog', function () {
            waitsFor('app to render', function () {
                return $('#g-app-body-container').length > 0;
            });

            runs(function () {
                file = new girder.models.FileModel({
                    _id: 'fake_id',
                    size: 12345,
                    name: 'my_file.txt',
                    sha512: sha512,
                    mimeType: 'text/plain',
                    created: '2016-06-28T14:58:59.235000+00:00'
                });

                new girder.views.widgets.FileInfoWidget({
                    model: file,
                    el: $('#g-dialog-container'),
                    parentView: app
                }).render();
            });

            girderTest.waitForDialog();

            runs(function () {
                var container = $('.g-file-info-line[property="sha512"]');
                expect(container.length).toBe(1);
                expect($('input.g-hash-textbox', container).val()).toBe(sha512);
                expect($('a.g-keyfile-download', container).attr('href')).toBe(
                    girder.rest.apiRoot + '/file/fake_id/hashsum_file/sha512'
                );
            });
        });
    });
});
