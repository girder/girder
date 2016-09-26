import _ from 'underscore';

import FileModel from 'girder/models/FileModel';
import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import FlowView from './FlowView';

import ItemViewTemplate from '../templates/itemView.pug';

// Show thumbnails on the item page
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

            headerEl.html(ItemViewTemplate());
        }
    }, this);

    render.call(this);
});
