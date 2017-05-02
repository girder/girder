import FileInfoWidget from 'girder/views/widgets/FileInfoWidget';
import { apiRoot, restRequest } from 'girder/rest';
import { AccessType } from 'girder/constants';
import { wrap } from 'girder/utilities/PluginUtils';

import template from '../templates/hashsumDownloadFileInfoWidget.pug';

import '../stylesheets/hashsumDownloadFileInfoWidget.styl';

var keyfileUrl = function (id, algo) {
    return `${apiRoot}/file/${id}/hashsum_file/${algo}`;
};

wrap(FileInfoWidget, 'render', function (render) {
    render.call(this);

    this.$('.g-file-info-line[property="id"]').before(template({
        file: this.model,
        parentItem: this.parentItem,
        keyfileUrl,
        AccessType
    }));

    this.$('.g-keyfile-download').tooltip();

    return this;
});

if (!FileInfoWidget.prototype.events) {
    FileInfoWidget.prototype.events = {};
}
FileInfoWidget.prototype.events['click .g-hashsum-compute'] = function () {
    restRequest({
        path: `file/${this.model.id}/hashsum`,
        type: 'POST',
        data: {
            'progress': true
        }
    }).done(resp => {
        this.model.set(resp);
        this.render();
    });
};
