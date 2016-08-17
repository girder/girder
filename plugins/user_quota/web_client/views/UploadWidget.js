import UploadWidget from 'girder/views/widgets/UploadWidget';

var UploadWidget_old_uploadNextFile = UploadWidget.prototype.uploadNextFile;

UploadWidget.prototype.uploadNextFile = function () {
    this.$('.g-drop-zone').addClass('hide');
    UploadWidget_old_uploadNextFile.call(this);
    this.currentFile.on('g:upload.error', function (info) {
        if (info.identifier === 'user_quota.upload-exceeds-quota') {
            this.$('.g-drop-zone').removeClass('hide');
        }
    }, this).on('g:upload.errorStarting', function (info) {
        if (info.identifier === 'user_quota.upload-exceeds-quota') {
            this.$('.g-drop-zone').removeClass('hide');
        }
    }, this);
};
