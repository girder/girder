/**
 * This widget is used to upload files to a folder. Pass a folder model
 * to its constructor as the parent folder that will be uploaded into.
 * Events:
 *   itemComplete: Triggered each time an individual item is finished uploading.
 *   finished: Triggered when the entire set of items is uploaded.
 */
girder.views.UploadWidget = girder.View.extend({
    events: {
        'submit #g-upload-form': 'startUpload',
        'click .g-resume-upload': function () {
            this.$('.g-upload-error-message').html('');
            this.currentFile.resumeUpload();
        },
        'change #g-files': function (e) {
            var files = this.$('#g-files')[0].files;

            if (files.length) {
                this.files = files;
                this.filesChanged();
            }
        },
        'click .g-drop-zone': function (e) {
            this.$('#g-files').click();
        },
        'dragenter .g-drop-zone': function (e) {
            e.stopPropagation();
            e.preventDefault();
            e.originalEvent.dataTransfer.dropEffect = 'copy';
            this.$('.g-drop-zone')
                .addClass('g-dropzone-show')
                .html('<i class="icon-bullseye"/> Drop files here');
        },
        'dragleave .g-drop-zone': function (e) {
            e.stopPropagation();
            e.preventDefault();
            this.$('.g-drop-zone')
                .removeClass('g-dropzone-show')
                .html('<i class="icon-docs"/> Browse or drop files');
        },
        'dragover .g-drop-zone': function (e) {
            e.preventDefault();
        },
        'drop .g-drop-zone': 'filesDropped'
    },

    initialize: function (settings) {
        this.parent = settings.parent || settings.folder;
        this.parentType = settings.parentType || 'folder';
        this.title = settings.title || 'Upload files';
        this.files = [];
        this.totalSize = 0;
    },

    render: function () {
        this.$el.html(jade.templates.uploadWidget({
            parent: this.parent,
            parentType: this.parentType,
            title: this.title
        })).girderModal(this).on('hidden.bs.modal', function () {
            girder.dialogs.handleClose('upload');
        });

        girder.dialogs.handleOpen('upload');
        return this;
    },

    filesDropped: function (e) {
        e.stopPropagation();
        e.preventDefault();
        this.$('.g-drop-zone')
            .removeClass('g-dropzone-show')
            .html('<i class="icon-docs"/> Browse or drop files');
        this.files = e.originalEvent.dataTransfer.files;
        this.filesChanged();
    },

    filesChanged: function () {
        if (this.files.length === 0) {
            this.$('.g-overall-progress-message').text('No files selected');
            this.$('.g-start-upload').addClass('disabled');
        } else {
            this.totalSize = 0;
            _.each(this.files, function (file) {
                this.totalSize += file.size;
            }, this);

            var msg;

            if (this.files.length > 1) {
                msg = 'Selected ' + this.files.length + ' files';
            } else {
                msg = 'Selected <b>' + this.files[0].name + '</b>';
            }
            this.$('.g-overall-progress-message').html('<i class="icon-ok"/> ' +
                msg + '  (' + girder.formatSize(this.totalSize) +
                ') -- Press start button');
            this.$('.g-start-upload').removeClass('disabled');
            this.$('.g-progress-overall,.g-progress-current').addClass('hide');
            this.$('.g-current-progress-message').empty();
            this.$('.g-upload-error-message').empty();
        }
    },

    startUpload: function (e) {
        e.preventDefault();

        this.$('.g-drop-zone').addClass('hide');
        this.$('.g-start-upload').addClass('disabled');
        this.$('.g-progress-overall,.g-progress-current').removeClass('hide');
        this.$('.g-upload-error-message').empty();

        this.currentIndex = 0;
        this.overallProgress = 0;
        this._uploadNextFile();
    },

    /**
     * Initializes the upload of a file by requesting the upload token
     * from the server. If successful, this will call _uploadChunk to send the
     * actual bytes from the file if it is of non-zero length.
     */
    _uploadNextFile: function () {
        if (this.currentIndex >= this.files.length) {
            // All files have finished
            this.$el.modal('hide');
            this.trigger('g:uploadFinished');
            return;
        }

        this.currentFile = this.parentType === 'file' ?
                this.parent : new girder.models.FileModel();

        this.currentFile.on('g:upload.complete', function () {
            this.currentIndex += 1;
            this._uploadNextFile();
        }, this).on('g:upload.chunkSent', function (info) {
            this.overallProgress += info.bytes;
        }, this).on('g:upload.progress', function (info) {
            var currentProgress = info.startByte + info.loaded;

            this.$('.g-progress-current>.progress-bar').css('width',
                Math.ceil(100 * currentProgress / info.total) + '%');
            this.$('.g-progress-overall>.progress-bar').css('width',
                Math.ceil(100 * (this.overallProgress + info.loaded) /
                          this.totalSize) + '%');
            this.$('.g-current-progress-message').html(
                '<i class="icon-doc-text"/>' + (this.currentIndex + 1) + ' of ' +
                    this.files.length + ' - <b>' + info.file.name + '</b>: ' +
                    girder.formatSize(currentProgress) + ' / ' +
                    girder.formatSize(info.total)
            );
            this.$('.g-overall-progress-message').html('Overall progress: ' +
                girder.formatSize(this.overallProgress + info.loaded) + ' / ' +
                girder.formatSize(this.totalSize));
        }, this).on('g:upload.error', function (info) {
            var html = info.message + ' <a class="g-resume-upload">' +
                'Click to resume upload</a>';
            $('.g-upload-error-message').html(html);
        }, this);

        if (this.parentType === 'file') {
            this.currentFile.updateContents(this.files[this.currentIndex]);
        } else {
            this.currentFile.upload(this.parent, this.files[this.currentIndex]);
        }
    }
});
