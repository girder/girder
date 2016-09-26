import $ from 'jquery';
import _ from 'underscore';

import FileModel from 'girder/models/FileModel';
import View from 'girder/views/View';
import { formatSize } from 'girder/misc';
import { handleClose, handleOpen } from 'girder/dialog';

import UploadWidgetTemplate from 'girder/templates/widgets/uploadWidget.pug';
import UploadWidgetNonModalTemplate from 'girder/templates/widgets/uploadWidgetNonModal.pug';

import 'girder/stylesheets/widgets/uploadWidget.styl';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

/**
 * This widget is used to upload files to a folder. Pass a folder model
 * to its constructor as the parent folder that will be uploaded into.
 * The events:
 *   itemComplete: Triggered each time an individual item is finished uploading.
 *   finished: Triggered when the entire set of items is uploaded.
 */
var UploadWidget = View.extend({
    events: {
        'submit #g-upload-form': function (e) {
            e.preventDefault();
            this.startUpload();
        },
        'click .g-resume-upload': function () {
            this.$('.g-upload-error-message').html('');
            this.currentFile.resumeUpload();
        },
        'click .g-restart-upload': function () {
            this.$('.g-upload-error-message').html('');
            this.uploadNextFile();
        },
        'change #g-files': function () {
            var files = this.$('#g-files')[0].files;

            if (files.length) {
                this.files = files;
                this.filesChanged();
            }
        },
        'click .g-drop-zone': function () {
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

    /**
     * This widget has several configuration options to control its view and
     * behavior. The following keys can be passed in the settings object:
     *
     * @param [parent] If the parent object is known when instantiating this
     * upload widget, pass the object here.
     * @param [parentType=folder] If the parent type is known when instantiating this
     * upload widget, pass the object here. Otherwise set noParent: true and
     * set it later, prior to starting the upload.
     * @param [noParent=false] If the parent object being uploaded into is not known
     * at the time of widget instantiation, pass noParent: true. Callers must
     * ensure that the parent is set by the time uploadNextFile() actually gets
     * called.
     * @param [title="Upload files"] Title for the widget. This is highly recommended
     * when rendering as a modal dialog. To disable rendering of the title, simply
     * pass a falsy object.
     * @param [modal=true] This widget normally renders as a modal dialog. Pass
     * modal: false to disable the modal behavior and simply render underneath a
     * parent element.
     * @param [overrideStart=false] Some callers will want to hook into the pressing
     * of the start upload button and add their own logic prior to actually sending
     * the files. To do so, set overrideStart: true and bind to the "g:uploadStarted"
     * event of this widget. The caller is then responsible for calling "uploadNextFile()"
     * on the widget when they have completed their actions and are ready to actually
     * send the files.
     *
     * Other events:
     *   - "g:filesChanged": This is triggered any time the user changes the
     *     file selection, either by dropping or browsing and selecting new files.
     *     Handlers will receive a single argument, which is the list of chosen files.
     *   - "g:uploadFinished": When all files have been successfully uploaded,
     *     this event is fired.
     */
    initialize: function (settings) {
        if (settings.noParent) {
            this.parent = null;
            this.parentType = null;
        } else {
            this.parent = settings.parent || settings.folder;
            this.parentType = settings.parentType || 'folder';
        }
        this.files = [];
        this.totalSize = 0;
        this.title = _.has(settings, 'title') ? settings.title : 'Upload files';
        this.modal = _.has(settings, 'modal') ? settings.modal : true;
        this.overrideStart = settings.overrideStart || false;
    },

    render: function () {
        if (this.modal) {
            this.$el.html(UploadWidgetTemplate({
                parent: this.parent,
                parentType: this.parentType,
                title: this.title
            }));

            var base = this;
            var dialogid;
            if (this.parentType === 'file') {
                dialogid = this.parent.get('_id');
            }

            this.$el.girderModal(this).on('hidden.bs.modal', function () {
                /* If we are showing the resume option, we have a partial upload
                 * that should be deleted, since the user has no way to get back
                 * to it. */
                if ($('.g-resume-upload').length && base.currentFile) {
                    base.currentFile.abortUpload();
                }
                handleClose('upload', undefined, dialogid);
            });

            handleOpen('upload', undefined, dialogid);
        } else {
            this.$el.html(UploadWidgetNonModalTemplate({
                parent: this.parent,
                parentType: this.parentType,
                title: this.title
            }));
        }
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
            this.setUploadEnabled(false);
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
                msg + '  (' + formatSize(this.totalSize) +
                ') -- Press start button');
            this.setUploadEnabled(true);
            this.$('.g-progress-overall,.g-progress-current').addClass('hide');
            this.$('.g-current-progress-message').empty();
            this.$('.g-upload-error-message').empty();
        }

        this.trigger('g:filesChanged', this.files);
    },

    startUpload: function () {
        this.setUploadEnabled(false);
        this.$('.g-drop-zone').addClass('hide');
        this.$('.g-progress-overall,.g-progress-current').removeClass('hide');
        this.$('.g-upload-error-message').empty();

        this.currentIndex = 0;
        this.overallProgress = 0;
        this.trigger('g:uploadStarted');

        if (!this.overrideStart) {
            this.uploadNextFile();
        }
    },

    /**
     * Enable or disable the start upload button.
     *
     * @param state {bool} Truthy for enabled, falsy for disabled.
     */
    setUploadEnabled: function (state) {
        this.$('.g-start-upload').girderEnable(state);
    },

    /**
     * Initializes the upload of a file by requesting the upload token
     * from the server. If successful, this will call _uploadChunk to send the
     * actual bytes from the file if it is of non-zero length.
     */
    uploadNextFile: function () {
        if (this.currentIndex >= this.files.length) {
            // All files have finished
            if (this.modal) {
                this.$el.modal('hide');
            }
            this.trigger('g:uploadFinished', {
                files: this.files,
                totalSize: this.totalSize
            });
            return;
        }

        this.currentFile = this.parentType === 'file'
                ? this.parent : new FileModel();

        this.currentFile.on('g:upload.complete', function () {
            this.currentIndex += 1;
            this.uploadNextFile();
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
                    formatSize(currentProgress) + ' / ' +
                    formatSize(info.total)
            );
            this.$('.g-overall-progress-message').html('Overall progress: ' +
                formatSize(this.overallProgress + info.loaded) + ' / ' +
                formatSize(this.totalSize));
        }, this).on('g:upload.error', function (info) {
            var html = info.message + ' <a class="g-resume-upload">' +
                'Click to resume upload</a>';
            $('.g-upload-error-message').html(html);
        }, this).on('g:upload.errorStarting', function (info) {
            var html = info.message + ' <a class="g-restart-upload">' +
                'Click to restart upload</a>';
            $('.g-upload-error-message').html(html);
        }, this);

        if (this.parentType === 'file') {
            this.currentFile.updateContents(this.files[this.currentIndex]);
        } else {
            this.currentFile.upload(this.parent, this.files[this.currentIndex]);
        }
    }
});

export default UploadWidget;

