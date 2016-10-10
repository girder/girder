import FileInfoWidget from 'girder/views/widgets/FileInfoWidget';
import { apiRoot } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';

import HashsumDownloadFileInfoWidgetTemplate from '../templates/hashsumDownloadFileInfoWidget.pug';

import '../stylesheets/hashsumDownloadFileInfoWidget.styl';

var keyfileUrl = function (id, algo) {
    return apiRoot + '/file/' + id + '/hashsum_file/' + algo;
};

wrap(FileInfoWidget, 'render', function (render) {
    render.call(this);

    this.$('.g-file-info-line[property="id"]').before(HashsumDownloadFileInfoWidgetTemplate({
        file: this.model,
        keyfileUrl: keyfileUrl
    }));

    this.$('.g-keyfile-download').tooltip();

    return this;
});
