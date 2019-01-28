import { wrap } from '@girder/core/utilities/PluginUtils';
import UploadWidget from '@girder/core/views/widgets/UploadWidget';

wrap(UploadWidget, 'uploadNextFile', function (uploadNextFile) {
    this.$('.g-drop-zone').addClass('hide');
    uploadNextFile.call(this);
    this.currentFile.on('g:upload.error', function (info) {
        if (info.identifier === 'user_quota.upload-exceeds-quota') {
            this.$('.g-drop-zone').removeClass('hide');
        }
    }, this).on('g:upload.errorStarting', function (info) {
        if (info.identifier === 'user_quota.upload-exceeds-quota') {
            this.$('.g-drop-zone').removeClass('hide');
        }
    }, this);
});
