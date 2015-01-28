/**
 * This widget shows a list of files in a given item.
 */
girder.views.FileListWidget = girder.View.extend({
    events: {
        'click a.g-show-more-files': function () {
            this.collection.fetchNextPage();
        },

        'click a.g-update-contents': function (e) {
            var cid = $(e.currentTarget).parent().attr('file-cid');
            this.uploadDialog(cid);
        },

        'click a.g-update-info': function (e) {
            var cid = $(e.currentTarget).parent().attr('file-cid');
            this.editFileDialog(cid);
        }
    },

    editFileDialog: function (cid) {
        this.editFileWidget = new girder.views.EditFileWidget({
            el: $('#g-dialog-container'),
            file: this.collection.get(cid),
            parentView: this
        }).off('g:saved', null, this).on('g:saved', function (file) {
            this.render();
        }, this);
        this.editFileWidget.render();
    },

    uploadDialog: function (cid) {
        new girder.views.UploadWidget({
            el: $('#g-dialog-container'),
            title: 'Replace file contents',
            parent: this.collection.get(cid),
            parentType: 'file',
            parentView: this
        }).on('g:uploadFinished', function () {
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: 'File contents updated.',
                type: 'success',
                timeout: 4000
            });
        }, this).render();
    },

    initialize: function (settings) {
        this.upload = settings.upload;
        this.fileEdit = settings.fileEdit;
        this.checked = [];
        this.collection = new girder.collections.FileCollection();
        this.collection.resourceName = 'item/' + settings.itemId + '/files';
        this.collection.append = true; // Append, don't replace pages
        this.collection.on('g:changed', function () {
            this.trigger('g:changed');
            this.render();
        }, this).fetch();
    },

    render: function () {
        this.checked = [];
        this.$el.html(girder.templates.fileList({
            files: this.collection.models,
            hasMore: this.collection.hasNextPage(),
            girder: girder
        }));

        this.$('.g-file-actions-container a[title]').tooltip({
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
        this.trigger('g:changed');
        this.render();
    }
});
