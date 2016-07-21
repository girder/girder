import App from 'girder/app';
import FileInfoWidget from 'girder/widgets/FileInfoWidget';
import FileModel from 'girder/models/FileModel';
import { apiRoot } from 'girder/rest';
import { events } from 'girder/events';

$(function () {
    girderTest.addCoveredScripts([
        '/static/built/plugins/hashsum_download/templates.js',
        '/plugins/hashsum_download/web_client/js/setup.js'
    ]);

    girderTest.importStylesheet(
        '/static/built/plugins/hashsum_download/plugin.min.css'
    );

    events.trigger('g:appload.before');
    var app = new App({
        el: 'body',
        parentView: null
    });
    events.trigger('g:appload.after');

    describe('Unit test the file view augmentation', function () {
        var file, files;
        var sha512 = 'd9f804f8f7caceec12a1207c16c6b70cb1dbfd8ea8f48a36168c98898c' +
            '1f138a11e9d1b40769d3c112afb099c6be5d57fc1ee8cf353df91ca0d3cf5524ddb047';

        it('Create a file and its info dialog', function () {
            waitsFor('app to render', function () {
                return $('#g-app-body-container').length > 0;
            });

            runs(function () {
                file = new FileModel({
                    _id: 'fake_id',
                    size: 12345,
                    name: 'my_file.txt',
                    sha512: sha512,
                    mimeType: 'text/plain',
                    created: '2016-06-28T14:58:59.235000+00:00'
                });

                new FileInfoWidget({
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
                    apiRoot + '/file/fake_id/hashsum_file/sha512'
                );
            });
        });
    });
});
