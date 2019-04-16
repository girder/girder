import $ from 'jquery';
import _ from 'underscore';

import FileCollection from '@girder/core/collections/FileCollection';
import FolderModel from '@girder/core/models/FolderModel';
import MetadataMixin from '@girder/core/models/MetadataMixin';
import Model from '@girder/core/models/Model';
import { restRequest } from '@girder/core/rest';

var ItemModel = Model.extend({
    resourceName: 'item',

    /**
     * Get the access level of the item if it is set. Takes an optional callback
     * to be called once the access level is fetched (or immediately if it has
     * already been fetched).
     */
    getAccessLevel: function (callback) {
        callback = callback || $.noop;

        if (this.has('_accessLevel')) {
            callback(this.get('_accessLevel'));
            return this.get('_accessLevel');
        }
        if (this.parent && this.parent.getAccessLevel()) {
            this.set('_accessLevel', this.parent.getAccessLevel());
            callback(this.get('_accessLevel'));
            return this.get('_accessLevel');
        } else {
            var parent = new FolderModel();
            parent.set({
                _id: this.get('folderId')
            }).once('g:fetched', function () {
                this.parent = parent;
                this.set('_accessLevel', this.parent.getAccessLevel());
                callback(this.get('_accessLevel'));
            }, this).fetch();
        }
    },

    /**
     * Get the path to the root of the hierarchy
     */
    getRootPath: function (callback) {
        return restRequest({
            url: `${this.resourceName}/${this.id}/rootpath`
        }).done((resp) => {
            callback(resp);
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    },

    /**
     * Get the files within the item.
     */
    getFiles: function () {
        return restRequest({
            url: `${this.resourceName}/${this.id}/files`
        }).then((resp) => {
            let fileCollection = new FileCollection(resp);
            this.trigger('g:files', fileCollection);
            return fileCollection;
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    }
});

_.extend(ItemModel.prototype, MetadataMixin);

export default ItemModel;
