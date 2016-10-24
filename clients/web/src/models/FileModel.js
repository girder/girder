import _ from 'underscore';

import FolderModel from 'girder/models/FolderModel';
import ItemModel from 'girder/models/ItemModel';
import Model from 'girder/models/Model';
import { restRequest, uploadHandlers, getUploadChunkSize } from 'girder/rest';

var FileModel = Model.extend({
    resourceName: 'file',
    resumeInfo: null,

    _wrapData: function (data, type) {
        var wrapped = data;

        if (!(data instanceof Blob)) {
            if (!_.isArray(data)) {
                wrapped = [data];
            }
            wrapped = new Blob(wrapped, {
                type: type
            });
        }

        return wrapped;
    },

    /**
     * Upload into an existing file object (i.e. this model) to change its
     * contents. This does not change the name or MIME type of the existing
     * file.
     * @param data A browser File object, browser Blob object, or raw data to be uploaded.
     */
    updateContents: function (data) {
        data = this._wrapData(data);

        this.upload(null, data, {
            path: 'file/' + this.get('_id') + '/contents',
            type: 'PUT',
            data: {
                size: data.size
            }
        });
    },

    /**
     * Upload data to a new file in a given container
     * @param Model A constructor for the parent model (either FolderModel or ItemModel).
     * @param model The parent model to upload to, or a string containing the id thereof.
     * @param data The data to upload - either a string, File object, or Blob object.
     * @param name The name of the file to create (optional if data is a File).
     * @param type The mime type of the file (optional).
     */
    _uploadToContainer: function (Model, model, data, name, type) {
        if (_.isString(model)) {
            model = new Model({
                _id: model
            });
        }

        data = this._wrapData(data, type);
        data.name = name;

        this.upload(model, data);
    },

    /**
     * Upload data to a new file in a given folder
     * @param parentFolder The parent folder to upload to, or a string containing the id thereof.
     * @param data The data to upload - either a string, File object, or Blob object.
     * @param name The name of the file to create (optional if data is a File).
     * @param type The mime type of the file (optional).
     */
    uploadToFolder: function (parentFolder, data, name, type) {
        this._uploadToContainer(FolderModel, parentFolder, data, name, type);
    },

    /**
     * Upload data to a new file in a given folder
     * @param parentItem The parent item to upload to, or a string containing the id thereof.
     * @param data The data to upload - either a string, File object, or Blob object.
     * @param name The name of the file to create (optional if data is a File).
     * @param type The mime type of the file (optional).
     */
    uploadToItem: function (parentItem, data, name, type) {
        this._uploadToContainer(ItemModel, parentItem, data, name, type);
    },

    /**
     * Upload a file. Handles uploading into all of the core assetstore types.
     * @param parentModel The parent folder or item to upload into.
     * @param file The browser File object to be uploaded.
     * @param [_restParams] Override the rest request parameters. This is meant
     * for internal use; do not pass this parameter.
     * @param [otherParams] Optional Object containing other parameters for the
     * initUpload request.
     */
    upload: function (parentModel, file, _restParams, otherParams) {
        this.startByte = 0;
        this.resumeInfo = null;
        this.uploadHandler = null;
        _restParams = _restParams || {
            path: 'file',
            type: 'POST',
            data: _.extend({
                parentType: parentModel.resourceName,
                parentId: parentModel.get('_id'),
                name: file.name,
                size: file.size,
                mimeType: file.type
            }, otherParams)
        };

        // Authenticate and generate the upload token for this file
        restRequest(_restParams).done(_.bind(function (upload) {
            var behavior = upload.behavior;
            if (behavior && uploadHandlers[behavior]) {
                this.uploadHandler = new uploadHandlers[behavior]({
                    upload: upload,
                    parentModel: parentModel,
                    file: file
                });
                this.uploadHandler.on({
                    'g:upload.complete': function (params) {
                        this.set(params);
                        this.trigger('g:upload.complete', params);
                        this.uploadHandler = null;
                    },
                    'g:upload.chunkSent': function (params) {
                        this.trigger('g:upload.chunkSent', params);
                    },
                    'g:upload.error': function (params) {
                        this.trigger('g:upload.error', params);
                    },
                    'g:upload.errorStarting': function (params) {
                        this.trigger('g:upload.errorStarting', params);
                    },
                    'g:upload.progress': function (params) {
                        this.trigger('g:upload.progress', {
                            startByte: params.startByte,
                            loaded: params.loaded,
                            total: params.file.size,
                            file: params.file
                        });
                    }
                }, this);
                return this.uploadHandler.execute();
            }

            if (file.size > 0) {
                // Begin uploading chunks of this file
                this._uploadChunk(file, upload._id);
            } else {
                // Empty file, so we are done
                this.set(upload);
                this.trigger('g:upload.complete');
            }
        }, this)).error(_.bind(function (resp) {
            var text = 'Error: ', identifier;

            if (resp.status === 0) {
                text += 'Connection to the server interrupted.';
            } else {
                text += resp.responseJSON.message;
                identifier = resp.responseJSON.identifier;
            }
            this.trigger('g:upload.errorStarting', {
                message: text,
                identifier: identifier,
                response: resp
            });
        }, this));
    },

    /**
     * If an error was triggered during the upload of this file, call this
     * in order to attempt to resume it.
     */
    resumeUpload: function () {
        if (this.uploadHandler !== null && this.uploadHandler.resume) {
            return this.uploadHandler.resume();
        }

        // Request the actual offset we need to resume at
        restRequest({
            path: 'file/offset',
            type: 'GET',
            data: {
                uploadId: this.resumeInfo.uploadId
            },
            error: null
        }).done(_.bind(function (resp) {
            this.startByte = resp.offset;
            this._uploadChunk(this.resumeInfo.file, this.resumeInfo.uploadId);
        }, this)).error(_.bind(function (resp) {
            var msg;

            if (resp.status === 0) {
                msg = 'Could not connect to the server.';
            } else {
                msg = 'An error occurred when resuming upload, check console.';
            }
            this.trigger('g:upload.error', {
                message: msg,
                response: resp
            });
        }, this));
    },

    abortUpload: function () {
        if (!this.resumeInfo || !this.resumeInfo.uploadId) {
            return;
        }
        restRequest({
            path: 'system/uploads',
            type: 'DELETE',
            data: {
                uploadId: this.resumeInfo.uploadId
            },
            error: null,
            done: null
        });
    },

    _uploadChunk: function (file, uploadId) {
        var endByte = Math.min(this.startByte + getUploadChunkSize(), file.size);

        this.chunkLength = endByte - this.startByte;
        var sliceFn = file.webkitSlice ? 'webkitSlice' : 'slice';
        var blob = file[sliceFn](this.startByte, endByte);
        var model = this;

        var fd = new FormData();
        fd.append('offset', this.startByte);
        fd.append('uploadId', uploadId);
        fd.append('chunk', blob);

        restRequest({
            path: 'file/chunk',
            type: 'POST',
            dataType: 'json',
            data: fd,
            contentType: false,
            processData: false,
            success: function (resp) {
                model.trigger('g:upload.chunkSent', {
                    bytes: endByte - model.startByte
                });

                if (endByte === file.size) {
                    model.startByte = 0;
                    model.resumeInfo = null;
                    model.set(resp);
                    model.trigger('g:upload.complete');
                } else {
                    model.startByte = endByte;
                    model._uploadChunk(file, uploadId);
                }
            },
            error: function (resp) {
                var text = 'Error: ', identifier;

                if (resp.status === 0) {
                    text += 'Connection to the server interrupted.';
                } else {
                    text += resp.responseJSON.message;
                    identifier = resp.responseJSON.identifier;
                }

                model.resumeInfo = {
                    uploadId: uploadId,
                    file: file
                };

                model.trigger('g:upload.error', {
                    message: text,
                    identifier: identifier,
                    response: resp
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

export default FileModel;
