import _ from 'underscore';
import Backbone from 'backbone';

import { restRequest, uploadHandlers } from '@girder/core/rest';

/**
 * This is the upload handler for the "s3" behavior, which is responsible for
 * uploading data to an s3 assetstore type directly from the user agent, using
 * either the single-request or multi-chunk protocol depending on the size of
 * the file.
 *
 * The flow here is to make requests to Girder for each required chunk of
 * the upload, which Girder authorizes and signs using HMAC. Those signatures
 * are sent, along with the bytes, to the appropriate S3 bucket. For multi-
 * chunk uploads, one final request is required after all chunks have been
 * sent in order to create the final unified record in S3.
 */
// Constructor
uploadHandlers.s3 = function (params) {
    this.params = params;
    this.startByte = 0;
    return _.extend(this, Backbone.Events);
};

var prototype = uploadHandlers.s3.prototype;

prototype._xhrProgress = function (event) {
    if (!event.lengthComputable) {
        return;
    }

    // We only want to count bytes of the actual file, not the bytes of
    // the request body corresponding to the other form parameters model
    // we are also sending.
    var loaded = this.payloadLength + event.loaded - event.total;

    if (loaded >= 0) {
        this.trigger('g:upload.progress', {
            startByte: this.startByte,
            loaded: loaded,
            total: this.params.file.size,
            file: this.params.file
        });
    }
};

prototype.execute = function () {
    var s3Info = this.params.upload.s3;

    var xhr = new XMLHttpRequest();
    xhr.open(s3Info.request.method, s3Info.request.url);
    _.each(s3Info.request.headers, (v, k) => {
        xhr.setRequestHeader(k, v);
    });

    if (s3Info.chunked) {
        this._multiChunkUpload(xhr);
    } else {
        this.payloadLength = this.params.file.size;
        xhr.onload = () => {
            if (xhr.status === 200) {
                this.trigger('g:upload.chunkSent', {
                    bytes: this.payloadLength
                });

                restRequest({
                    url: 'file/completion',
                    method: 'POST',
                    data: {
                        uploadId: this.params.upload._id
                    },
                    error: null
                }).done((resp) => {
                    this.trigger('g:upload.complete', resp);
                }).fail((resp) => {
                    var msg;

                    if (resp.status === 0) {
                        msg = 'Could not connect to the server.';
                    } else {
                        msg = 'An error occurred when resuming upload, check console.';
                    }
                    this.trigger('g:upload.error', {
                        message: msg
                    });
                });
            } else {
                this.trigger('g:upload.error', {
                    message: 'Error occurred uploading to S3 (' + xhr.status + ').'
                });
            }
        };

        xhr.upload.addEventListener('progress', (event) => {
            this._xhrProgress(event);
        });

        xhr.addEventListener('error', (event) => {
            this.trigger('g:upload.error', {
                message: 'Error occurred uploading to S3.',
                event: event
            });
        });

        xhr.send(this.params.file);
    }
};

prototype.resume = function () {
    if (this.params.upload.s3.chunked) {
        return this._sendNextChunk();
    }

    // If this is a single-chunk upload, we have to use the offset method
    // to re-generate the initial request with a new timestamp.
    restRequest({
        url: 'file/offset',
        method: 'GET',
        data: {
            uploadId: this.params.upload._id
        },
        error: null
    }).done((resp) => {
        this.params.upload.s3.request = resp;
        this.execute();
    }).fail((resp) => {
        var msg;

        if (resp.status === 0) {
            msg = 'Could not connect to the Girder server.';
        } else {
            msg = 'An error occurred when resuming upload, check console.';
        }
        this.trigger('g:upload.error', {
            message: msg
        });
    });
};

/**
 * If the file being uploaded is larger than a single chunk length, it
 * should be uploaded using the S3 multipart protocol.
 */
prototype._multiChunkUpload = function (xhr) {
    this.eTagList = {};
    this.startByte = 0;
    this.chunkN = 1;

    xhr.onload = () => {
        if (xhr.status === 200) {
            this.s3UploadId = xhr.responseText.match(/<UploadId>(.*)<\/UploadId>/).pop();
            this._sendNextChunk();
        } else {
            this.trigger('g:upload.error', {
                message: 'Error while initializing multichunk S3 upload.',
                event: event
            });
        }
    };

    xhr.addEventListener('error', (event) => {
        this.trigger('g:upload.error', {
            message: 'Error occurred uploading to S3.',
            event: event
        });
    });

    xhr.send();
};

/**
 * Internal helper method used during multichunk upload protocol. This
 * requests a signed chunk upload request from Girder, then uses that
 * authorized request to send the chunk to S3.
 */
prototype._sendNextChunk = function () {
    var sliceFn = this.params.file.webkitSlice ? 'webkitSlice' : 'slice';
    var data = this.params.file[sliceFn](this.startByte,
        this.startByte + this.params.upload.s3.chunkLength);
    this.payloadLength = data.size;

    // Get the authorized request from Girder
    restRequest({
        url: 'file/chunk',
        method: 'POST',
        data: {
            offset: 0,
            chunk: JSON.stringify({
                s3UploadId: this.s3UploadId,
                partNumber: this.chunkN,
                contentLength: this.payloadLength
            }),
            uploadId: this.params.upload._id
        },
        error: null
    }).done((resp) => {
        // Send the chunk to S3
        var xhr = new XMLHttpRequest();
        xhr.open(resp.s3.request.method, resp.s3.request.url);

        xhr.onload = () => {
            if (xhr.status === 200) {
                this.trigger('g:upload.chunkSent', {
                    bytes: this.payloadLength
                });
                this.eTagList[this.chunkN] = xhr.getResponseHeader('ETag');
                this.startByte += this.payloadLength;
                this.chunkN += 1;

                if (this.startByte < this.params.file.size) {
                    this._sendNextChunk();
                } else {
                    this._finalizeMultiChunkUpload();
                }
            } else {
                this.trigger('g:upload.error', {
                    message: 'Error occurred uploading to S3 (' + xhr.status + ').'
                });
            }
        };

        xhr.upload.addEventListener('progress', (event) => {
            this._xhrProgress(event);
        });

        xhr.addEventListener('error', (event) => {
            this.trigger('g:upload.error', {
                message: 'Error occurred uploading to S3.',
                event: event
            });
        });

        xhr.send(data);
    }).fail(() => {
        this.trigger('g:upload.error', {
            message: 'Error getting signed chunk request from Girder.'
        });
    });
};

/**
 * When all chunks of a multichunk upload have been sent, this must be
 * called in order to finalize the upload.
 */
prototype._finalizeMultiChunkUpload = function () {
    restRequest({
        url: 'file/completion',
        method: 'POST',
        data: {
            uploadId: this.params.upload._id
        },
        error: null
    }).done((resp) => {
        // Create the XML document that will be the request body to S3
        var doc = document.implementation.createDocument(null, null, null);
        var root = doc.createElement('CompleteMultipartUpload');

        _.each(this.eTagList, (etag, partNumber) => {
            var partEl = doc.createElement('Part');
            var partNumberEl = doc.createElement('PartNumber');
            var etagEl = doc.createElement('ETag');

            partNumberEl.appendChild(doc.createTextNode(partNumber));
            etagEl.appendChild(doc.createTextNode(etag));
            partEl.appendChild(partNumberEl);
            partEl.appendChild(etagEl);
            root.appendChild(partEl);
        });

        var req = resp.s3FinalizeRequest;
        var xhr = new XMLHttpRequest();

        xhr.open(req.method, req.url);

        _.each(req.headers, (v, k) => {
            xhr.setRequestHeader(k, v);
        });

        xhr.onload = () => {
            if (xhr.status === 200) {
                delete resp.s3FinalizeRequest;
                this.trigger('g:upload.complete', resp);
            } else {
                this.trigger('g:upload.error', {
                    message: 'Error occurred uploading to S3 (' + xhr.status + ').'
                });
            }
        };

        xhr.send(new window.XMLSerializer().serializeToString(root));
    }).fail((resp) => {
        var msg;

        if (resp.status === 0) {
            msg = 'Could not connect to the server.';
        } else {
            msg = 'Upload error during finalize, check console.';
        }
        this.trigger('g:upload.error', {
            message: msg
        });
    });
};
