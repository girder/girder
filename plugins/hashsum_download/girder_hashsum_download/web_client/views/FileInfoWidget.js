import template from '../templates/hashsumDownloadFileInfoWidget.pug';

import '../stylesheets/hashsumDownloadFileInfoWidget.styl';

const FileInfoWidget = girder.views.widgets.FileInfoWidget;
const { getApiRoot, restRequest } = girder.rest;
const { AccessType } = girder.constants;
const { wrap } = girder.utilities.PluginUtils;

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
            progress: true
        }
    }).done((resp) => {
        this.model.set(resp);
        this.render();
    });
};
