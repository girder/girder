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
        'change #g-files': 'filesChanged'
    },

    initialize: function (settings) {
        this.folder = settings.folder;
        this.files = [];
        this.totalSize = 0;
    },

    render: function () {
        this.$el.html(jade.templates.uploadWidget({
            folder: this.folder
        })).modal();

        return this;
    },

    filesChanged: function () {
        this.files = this.$('#g-files')[0].files;
        if (this.files.length === 0) {
            this.$('.g-upload-progress-message').text('No files selected');
            this.$('.g-start-upload').addClass('disabled');
        }
        else {
            this.totalSize = 0;
            _.each(this.files, function (file) {
                this.totalSize += file.size;
            }, this);
            this.$('.g-overall-progress-message').text(
                'Selected ' + this.files.length + ' files (' +
                girder.formatSize(this.totalSize) +
                ') -- Press start button');
            this.$('.g-start-upload').removeClass('disabled');
        }
    },

    startUpload: function (e) {
        e.preventDefault();

        this.$('.g-start-upload').addClass('disabled');
        this.$('.g-progress-overall,.g-progress-current').removeClass('hide');

        this.currentIndex = 0;
        this.overallProgress = 0;
        this.resumeUploadId = null;
        this._uploadNextFile();
    },

    /**
     * Initializes the upload of a file by requesting the upload token
     * from the server. If successful, this will call _uploadChunk to send the
     * actual bytes from the file if it is of non-zero length. Calling this
     * will also resume an interrupted upload.
     */
    _uploadNextFile: function () {
        if (this.currentIndex >= this.files.length) {
            return; // All files have finished
        }

        if (this.resumeUploadId) {
            // Resume the upload that was interrupted
            this._uploadChunk(this.resumeUploadId);
        }
        else {
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
        }
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
            error: function (e) {
                // TODO show some error message and enable resume mode
                this.resumeUploadId = uploadId;
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
        this.$('.g-current-progress-message').html('<b>' + file.name +
            '</b> - ' + girder.formatSize(this.startByte + loaded) + ' / ' +
            girder.formatSize(file.size));
        this.$('.g-overall-progress-message').html('Uploading file ' +
            (this.currentIndex + 1) + ' of ' + this.files.length + ' - ' +
            girder.formatSize(this.overallProgress + loaded) + ' / ' +
            girder.formatSize(this.totalSize));
    }
});
