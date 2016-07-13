import _ from 'underscore';
import Backbone from 'backbone';

import router from 'girder/router';
import { AccessType } from 'girder/constants';
import { wrap } from 'girder/utilities/PluginUtils';

import FileListWidget from 'girder/views/widgets/FileListWidget';

// Add create thumbnail link to each file in the file list
import createButtonTemplate from './templates/createButton.jade';
wrap(FileListWidget, 'render', function (render) {
    render.call(this);

    if (this.parentItem.getAccessLevel() >= AccessType.WRITE) {
        this.$('.g-file-actions-container').prepend(createButtonTemplate());
        this.$('.g-create-thumbnail').tooltip({
            container: 'body',
            placement: 'auto',
            delay: 100
        });
    }

    return this;
});

// Bind the thumbnail creation button
import CreateThumbnailView from './views/CreateThumbnailView';
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

// Show thumbnails on the item page
import ItemView from 'girder/views/body/ItemView';
import FileModel from 'girder/models/FileModel';
import FlowView from './views/FlowView';
import itemHeaderTemplate from './templates/itemHeader.jade';
wrap(ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        var thumbnails = _.map(this.model.get('_thumbnails'), function (id) {
            return new FileModel({_id: id});
        });

        if (thumbnails && thumbnails.length) {
            var el = $('<div>', {
                class: 'g-thumbnails-flow-view-container'
            }).prependTo(this.$('.g-item-info'));

            new FlowView({
                parentView: this,
                thumbnails: thumbnails,
                accessLevel: this.model.getAccessLevel(),
                el: el
            }).render();

            var headerEl = $('<div>', {
                class: 'g-thumbnails-header-container'
            }).prependTo(this.$('.g-item-info'));

            headerEl.html(itemHeaderTemplate());
        }
    }, this);

    render.call(this);
});
