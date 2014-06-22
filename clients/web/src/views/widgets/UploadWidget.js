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
        'click .g-resume-upload': 'resumeUpload',
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
        this.folder = settings.folder;
        this.files = [];
        this.totalSize = 0;
    },

    render: function () {
        this.$el.html(jade.templates.uploadWidget({
            folder: this.folder
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
        }
        else {
            this.totalSize = 0;
            _.each(this.files, function (file) {
                this.totalSize += file.size;
            }, this);
            this.$('.g-overall-progress-message').html('<i class="icon-ok"/>' +
                ' Selected ' + this.files.length + ' files (' +
                girder.formatSize(this.totalSize) +
                ') -- Press start button');
            this.$('.g-start-upload').removeClass('disabled');
            this.$('.g-progress-overall,.g-progress-current').addClass('hide');
            this.$('.g-current-progress-message').html('');
            this.$('.g-upload-error-message').html('');
        }
    },

    startUpload: function (e) {
        e.preventDefault();

        this.$('.g-drop-zone').addClass('hide');
        this.$('.g-start-upload').addClass('disabled');
        this.$('.g-progress-overall,.g-progress-current').removeClass('hide');
        this.$('.g-upload-error-message').html('');

        this.currentIndex = 0;
        this.overallProgress = 0;
        this.resumeUploadId = null;
        this._uploadNextFile();
    },

    resumeUpload: function () {
        this.$('.g-upload-error-message').html('');

        // Request the actual offset we need to start at
        girder.restRequest({
            path: 'file/offset',
            type: 'GET',
            data: {
                'uploadId': this.resumeUploadId
            }
        }).done(_.bind(function (resp) {
            this.startByte = resp.offset;
            this._uploadChunk(this.resumeUploadId);
        }, this));
    },

    /**
     * Initializes the upload of a file by requesting the upload token
     * from the server. If successful, this will call _uploadChunk to send the
     * actual bytes from the file if it is of non-zero length. Calling this
     * will also resume an interrupted upload.
     */
    _uploadNextFile: function () {
        if (this.currentIndex >= this.files.length) {
            // All files have finished
            this.$el.modal('hide');
            this.trigger('g:uploadFinished');
            return;
        }

        var fileModel = new girder.models.FileModel();
        fileModel.on('g:upload.complete', function (info) {
            this.overallProgress += info.bytesSent;
            this.currentIndex += 1;
            this._uploadNextFile();
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
                girder.formatSize(info.total));
            this.$('.g-overall-progress-message').html('Overall progress: ' +
                girder.formatSize(this.overallProgress + info.loaded) + ' / ' +
                girder.formatSize(this.totalSize));
        }, this).on('g:upload.error', function (info) {
            var text = info.message + ' <a class="g-resume-upload">' +
                'Click to resume upload</a>';
            $('.g-upload-error-message').html(text);
            // TODO set necessary resume info
        }, this).upload(this.folder, this.files[this.currentIndex]);
    }
});
