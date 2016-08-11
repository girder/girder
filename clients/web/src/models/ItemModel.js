import $ from 'jquery';
import _ from 'underscore';

import FolderModel from 'girder/models/FolderModel';
import MetadataMixin from 'girder/models/MetadataMixin';
import Model from 'girder/models/Model';
import { restRequest } from 'girder/rest';

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
            this.parent = new FolderModel();
            this.parent.set({
                _id: this.get('folderId')
            }).once('g:fetched', function () {
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
            path: this.resourceName + '/' + this.get('_id') + '/rootpath'
        }).done(_.bind(function (resp) {
            callback(resp);
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    }
});

_.extend(ItemModel.prototype, MetadataMixin);

export default ItemModel;
