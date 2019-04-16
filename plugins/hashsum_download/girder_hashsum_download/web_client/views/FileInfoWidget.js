import FileInfoWidget from '@girder/core/views/widgets/FileInfoWidget';
import { getApiRoot, restRequest } from '@girder/core/rest';
import { AccessType } from '@girder/core/constants';
import { wrap } from '@girder/core/utilities/PluginUtils';

import template from '../templates/hashsumDownloadFileInfoWidget.pug';

import '../stylesheets/hashsumDownloadFileInfoWidget.styl';

var keyfileUrl = function (id, algo) {
    return `${getApiRoot()}/file/${id}/hashsum_file/${algo}`;
};

wrap(FileInfoWidget, 'render', function (render) {
    render.call(this);

    this.$('.g-file-info-line[property="id"]').before(template({
        file: this.model,
        parentItem: this.parentItem,
        keyfileUrl,
        AccessType
    }));

    return this;
});

if (!FileInfoWidget.prototype.events) {
    FileInfoWidget.prototype.events = {};
}
FileInfoWidget.prototype.events['click .g-hashsum-compute'] = function () {
    restRequest({
        url: `file/${this.model.id}/hashsum`,
        method: 'POST',
        data: {
            'progress': true
        }
    }).done((resp) => {
        this.model.set(resp);
        this.render();
    });
};
