import $ from 'jquery';
import _ from 'underscore';

import EditFileWidget from 'girder/views/widgets/EditFileWidget';
import FileCollection from 'girder/collections/FileCollection';
import FileInfoWidget from 'girder/views/widgets/FileInfoWidget';
import UploadWidget from 'girder/views/widgets/UploadWidget';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { confirm } from 'girder/dialog';
import { formatSize } from 'girder/misc';
import events from 'girder/events';

import FileListTemplate from 'girder/templates/widgets/fileList.pug';

import 'bootstrap/js/tooltip';

/**
 * This widget shows a list of files in a given item.
 */
var FileListWidget = View.extend({
    events: {
        'click a.g-show-more-files': function () {
            this.collection.fetchNextPage();
        },

        'click a.g-show-info': function (e) {
            var cid = $(e.currentTarget).attr('file-cid');
            new FileInfoWidget({
                el: $('#g-dialog-container'),
                model: this.collection.get(cid),
                parentView: this
            }).render();
        },

        'click a.g-update-contents': function (e) {
            var cid = $(e.currentTarget).parent().attr('file-cid');
            this.uploadDialog(cid);
        },

        'click a.g-update-info': function (e) {
            var cid = $(e.currentTarget).parent().attr('file-cid');
            this.editFileDialog(cid);
        },

        'click a.g-delete-file': function (e) {
            var cid = $(e.currentTarget).parent().attr('file-cid');
            var file = this.collection.get(cid);

            confirm({
                text: 'Are you sure you want to delete the file <b>' +
                      file.escape('name') + '</b>?',
                yesText: 'Delete',
                escapedHtml: true,
                confirmCallback: _.bind(function () {
                    file.once('g:deleted', function () {
                        events.trigger('g:alert', {
                            icon: 'ok',
                            type: 'success',
                            text: 'File deleted.',
                            timeout: 4000
                        });

                        this.render();
                    }, this).once('g:error', function () {
                        events.trigger('g:alert', {
                            icon: 'cancel',
                            text: 'Failed to delete file.',
                            type: 'danger',
                            timeout: 4000
                        });
                    }).destroy();
                }, this)
            });
        }
    },

    initialize: function (settings) {
        this.upload = settings.upload;
        this.fileEdit = settings.fileEdit;
        this.checked = [];
        this.collection = new FileCollection();
        this.collection.altUrl = 'item/' +
            (settings.itemId || settings.item.get('_id')) + '/files';
        this.collection.append = true; // Append, don't replace pages
        this.collection.on('g:changed', function () {
            this.render();
            this.trigger('g:changed');
        }, this).fetch();

        this.parentItem = settings.item;
    },

    editFileDialog: function (cid) {
        this.editFileWidget = new EditFileWidget({
            el: $('#g-dialog-container'),
            file: this.collection.get(cid),
            parentView: this
        }).off('g:saved', null, this).on('g:saved', function () {
            this.render();
        }, this);
        this.editFileWidget.render();
    },

    uploadDialog: function (cid) {
        new UploadWidget({
            el: $('#g-dialog-container'),
            title: 'Replace file contents',
            parent: this.collection.get(cid),
            parentType: 'file',
            parentView: this
        }).on('g:uploadFinished', function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'File contents updated.',
                type: 'success',
                timeout: 4000
            });
        }, this).render();
    },

    render: function () {
        this.checked = [];
        this.$el.html(FileListTemplate({
            files: this.collection.toArray(),
            hasMore: this.collection.hasNextPage(),
            AccessType: AccessType,
            formatSize: formatSize,
            parentItem: this.parentItem
        }));

        this.$('.g-file-list-entry a[title]').tooltip({
            container: 'body',
            placement: 'auto',
            delay: 100
        });

        if (this.fileEdit) {
            this.editFileDialog(this.fileEdit);
            this.fileEdit = false;
        } else if (this.upload) {
            this.uploadDialog(this.upload);
            this.upload = false;
        }

        return this;
    },

    /**
     * Insert a file into the collection and re-render it.
     */
    insertFile: function (file) {
        this.collection.add(file);
        this.render();
        this.trigger('g:changed');
    }
});

export default FileListWidget;

