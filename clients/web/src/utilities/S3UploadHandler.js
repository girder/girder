/**
 * This is the upload handler for the "s3" behavior, which is responsible for
 * uploading data to an s3 assetstore type directly from the user agent, using
 * either the single-request or multi-chunk protocol depending on the size of
 * the file.
 *
 * The flow here is to make requests to girder for each required chunk of
 * the upload, which girder authorizes and signs using HMAC. Those signatures
 * are sent, along with the bytes, to the appropriate S3 bucket. For multi-
 * chunk uploads, one final request is required after all chunks have been
 * sent in order to create the final unified record in S3.
 */
(function () {
    girder.uploadHandlers.s3 = function (params) {
        this.params = params;
        this.startByte = 0;
        return _.extend(this, Backbone.Events);
    };

    girder.uploadHandlers.s3.prototype._xhrProgress = function (event) {
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

    girder.uploadHandlers.s3.prototype.execute = function () {
        var s3Info = this.params.upload.s3;
        var handler = this;

        var xhr = new XMLHttpRequest();
        xhr.open(s3Info.request.method, s3Info.request.url);
        _.each(s3Info.request.headers, function (v, k) {
            xhr.setRequestHeader(k, v);
        });

        if (s3Info.chunked) {
            console.log('Chunked uploading not supported yet!');
        }
        else {
            this.payloadLength = this.params.file.size;
            xhr.onload = function () {
                if (xhr.status === 200) {
                    console.log('DONE!'); // TODO FINALIZE to girder
                } else {
                    handler.trigger('g:upload.error', {
                        message: 'Error occurred uploading to S3 (' +
                            xhr.status + ').',
                        event: event
                    });
                }
            };
            xhr.addEventListener('error', function (event) {
                handler.trigger('g:upload.error', {
                    message: 'Error occurred uploading to S3.',
                    event: event
                });
            });
            xhr.upload.addEventListener('progress', function (event) {
                handler._xhrProgress.call(handler, event)
            });

            xhr.send(this.params.file);
        }
    };
}) ();
