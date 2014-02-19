/**
 * This widget is used to upload files to a folder. Pass a folder model
 * to its constructor as the parent folder that will be uploaded into.
 * Events:
 *   itemComplete: Triggered each time an individual item is finished uploading.
 *   finished: Triggered when the entire set of items is uploaded.
 */
girder.views.UploadWidget = Backbone.View.extend({
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
        })).girderModal(this);

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

        var file = this.files[this.currentIndex];
        // Authenticate and generate the upload token for this file
        girder.restRequest({
            path: 'file',
            type: 'POST',
            data: {
                'parentType': 'folder',
                'parentId': this.folder.get('_id'),
                'name': file.name,
                'size': file.size
            }
        }).done(_.bind(function (upload) {
            if (file.size > 0) {
                // Begin uploading chunks of this file
                this.startByte = 0;
                this._uploadChunk(upload._id);
            }
            else {
                // Empty file, so we are done
                this.currentIndex += 1;
                this._uploadNextFile();
            }
        }, this));
    },

    /**
     * Reads and uploads a chunk of the file starting at startByte. Pass
     * the uploadId generated in _uploadNextFile.
     */
    _uploadChunk: function (uploadId) {
        var file = this.files[this.currentIndex];
        var endByte = Math.min(this.startByte + girder.UPLOAD_CHUNK_SIZE,
                               file.size);

        this.chunkLength = endByte - this.startByte;

        var blob = file.slice(this.startByte, endByte);
        var view = this;

        var fd = new FormData();
        fd.append('offset', view.startByte);
        fd.append('uploadId', uploadId);
        fd.append('chunk', blob);

        $.ajax({
            url: girder.apiRoot + '/file/chunk',
            type: 'POST',
            dataType: 'json',
            data: fd,
            contentType: false,
            processData: false,
            success: function () {
                view.overallProgress += endByte - view.startByte;
                if (endByte === file.size) {
                    view.resumeUploadId = null;
                    view.startByte = 0;
                    view.currentIndex += 1;
                    view._uploadNextFile();
                }
                else {
                    view.startByte = endByte;
                    view._uploadChunk(uploadId);
                }
            },
            error: function (xhr) {
                var text = 'Error: ';

                if (xhr.status === 0) {
                    text += 'Connection to the server interrupted.';
                }
                else {
                    text += xhr.responseJSON.message;
                }
                text += ' <a class="g-resume-upload">' +
                    'Click to resume upload</a>';
                view.$('.g-upload-error-message').html(text);
                view.resumeUploadId = uploadId;
            },
            xhr: function () {
                // Custom XHR so we can register a progress handler
                var xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener('progress', function (e) {
                    view._uploadProgress(e);
                });
                return xhr;
            }
        });
    },

    /**
     * Progress callback from XHR during upload. This will update the bar
     * and the text accordingly.
     */
    _uploadProgress: function (e) {
        if (!e.lengthComputable) {
            return;
        }

        var file = this.files[this.currentIndex];
        // We only want to count bytes of the actual file, not the bytes of
        // the request body corresponding to the other form parameters that
        // we are also sending.
        var loaded = this.chunkLength + e.loaded - e.total;

        if (loaded < 0) {
            return;
        }

        this.$('.g-progress-current>.progress-bar').css('width',
            Math.ceil(100 * (this.startByte + loaded) / file.size) + '%');
        this.$('.g-progress-overall>.progress-bar').css('width',
            Math.ceil(100 * (this.overallProgress + loaded) / this.totalSize) +
            '%');
        this.$('.g-current-progress-message').html(
            '<i class="icon-doc-text"/>' + (this.currentIndex + 1) + ' of ' +
            this.files.length + ' - <b>' + file.name + '</b>: ' +
            girder.formatSize(this.startByte + loaded) + ' / ' +
            girder.formatSize(file.size));
        this.$('.g-overall-progress-message').html('Overall progress: ' +
            girder.formatSize(this.overallProgress + loaded) + ' / ' +
            girder.formatSize(this.totalSize));
    }
});
