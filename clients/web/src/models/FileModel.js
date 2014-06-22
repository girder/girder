girder.models.FileModel = girder.Model.extend({
    resourceName: 'file',

    /**
     * Upload a file. Handles uploading into all of the core assetstore types.
     * @param parentModel The parent folder or item to upload into.
     * @param file The browser File object to be uploaded.
     */
    upload: function (parentModel, file) {
        this.startByte = 0;
        // Authenticate and generate the upload token for this file
        girder.restRequest({
            path: 'file',
            type: 'POST',
            data: {
                'parentType': parentModel.resourceName,
                'parentId': parentModel.get('_id'),
                'name': file.name,
                'size': file.size,
                'mimeType': file.type
            }
        }).done(_.bind(function (upload) {
            if (file.size > 0) {
                // Begin uploading chunks of this file
                this._uploadChunk(file, upload._id);
            }
            else {
                // Empty file, so we are done
                this.trigger('g:upload.complete', {
                    bytesSent: 0
                });
            }
        }, this));
    },

    _uploadChunk: function (file, uploadId) {
        var endByte = Math.min(this.startByte + girder.UPLOAD_CHUNK_SIZE,
                               file.size);

        this.chunkLength = endByte - this.startByte;

        var blob = file.slice(this.startByte, endByte);
        var model = this;

        var fd = new FormData();
        fd.append('offset', this.startByte);
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
                if (endByte === file.size) {
                    model.resumeUploadId = null;
                    model.startByte = 0;
                    model.trigger('g:upload.complete', {
                        bytesSent: endByte - model.startByte
                    });
                }
                else {
                    model.startByte = endByte;
                    model._uploadChunk(file, uploadId);
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

                model.resumeUploadId = uploadId;
                model.trigger('g:upload.error', {
                    uploadId: uploadId,
                    message: text
                });

            },
            xhr: function () {
                // Custom XHR so we can register a progress handler
                var xhr = new window.XMLHttpRequest();
                xhr.upload.addEventListener('progress', function (e) {
                    model._uploadProgress(file, e);
                });
                return xhr;
            }
        });
    },

    /**
     * Progress callback from XHR during upload. This will trigger useful
     * progress events under the 'upload.progress' tag.
     */
    _uploadProgress: function (file, event) {
        if (!event.lengthComputable) {
            return;
        }

        // We only want to count bytes of the actual file, not the bytes of
        // the request body corresponding to the other form parameters model
        // we are also sending.
        var loaded = this.chunkLength + event.loaded - event.total;

        if (loaded >= 0) {
            this.trigger('g:upload.progress', {
                startByte: this.startByte,
                loaded: loaded,
                total: file.size,
                file: file
            });
        }
    }
});
