import Backbone from 'backbone';

import FileListWidget from 'girder/views/widgets/FileListWidget';
import router from 'girder/router';
import { AccessType } from 'girder/constants';
import { wrap } from 'girder/utilities/PluginUtils';

import CreateThumbnailView from './CreateThumbnailView';

import FileListWidgetCreateButtonTemplate from '../templates/fileListWidgetCreateButton.pug';

// Add create thumbnail link to each file in the file list
wrap(FileListWidget, 'render', function (render) {
    render.call(this);

    if (this.parentItem.getAccessLevel() >= AccessType.WRITE) {
        this.$('.g-file-actions-container').prepend(FileListWidgetCreateButtonTemplate());
        this.$('.g-create-thumbnail').tooltip({
            container: 'body',
            placement: 'auto',
            delay: 100
        });
    }

    return this;
});

// Bind the thumbnail creation button
FileListWidget.prototype.events['click a.g-create-thumbnail'] = function (e) {
    var cid = $(e.currentTarget).parent().attr('file-cid');

    new CreateThumbnailView({
        el: $('#g-dialog-container'),
        parentView: this,
        item: this.parentItem,
        file: this.collection.get(cid)
    }).once('g:created', function (params) {
        Backbone.history.fragment = null;
        router.navigate(params.attachedToType + '/' + params.attachedToId, {trigger: true});
    }, this).render();
};
