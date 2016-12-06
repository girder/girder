import $ from 'jquery';
import _ from 'underscore';

import EditItemWidget from 'girder/views/widgets/EditItemWidget';
import FileListWidget from 'girder/views/widgets/FileListWidget';
import ItemBreadcrumbWidget from 'girder/views/widgets/ItemBreadcrumbWidget';
import ItemModel from 'girder/models/ItemModel';
import MetadataWidget from 'girder/views/widgets/MetadataWidget';
import router from 'girder/router';
import UploadWidget from 'girder/views/widgets/UploadWidget';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { cancelRestRequests } from 'girder/rest';
import { confirm, handleClose } from 'girder/dialog';
import events from 'girder/events';
import { formatSize, formatDate, renderMarkdown, DATE_SECOND } from 'girder/misc';

import ItemPageTemplate from 'girder/templates/body/itemPage.pug';

import 'girder/stylesheets/body/itemPage.styl';

import 'bootstrap/js/dropdown';
import 'bootstrap/js/tooltip';

/**
 * This view shows a single item's page.
 */
var ItemView = View.extend({
    events: {
        'click .g-edit-item': 'editItem',
        'click .g-delete-item': 'deleteItem',
        'click .g-upload-into-item': 'uploadIntoItem'
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.edit = settings.edit || false;
        this.fileEdit = settings.fileEdit || false;
        this.upload = settings.upload || false;

        // If collection model is already passed, there is no need to fetch.
        if (settings.item) {
            this.model = settings.item;
            this.render();
        } else {
            console.error('Implement fetch then render item');
        }
    },

    uploadIntoItem: function () {
        new UploadWidget({
            el: $('#g-dialog-container'),
            parent: this.model,
            parentType: 'item',
            parentView: this
        }).on('g:uploadFinished', function () {
            handleClose('upload');
            this.upload = false;

            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Files added.',
                type: 'success',
                timeout: 4000
            });

            this.fileListWidget.collection.fetch(null, true);
        }, this).render();
    },

    editItem: function () {
        var container = $('#g-dialog-container');

        if (!this.editItemWidget) {
            this.editItemWidget = new EditItemWidget({
                el: container,
                item: this.model,
                parentView: this
            }).off('g:saved').on('g:saved', function () {
                this.render();
            }, this);
        }
        this.editItemWidget.render();
    },

    deleteItem: function () {
        var folderId = this.model.get('folderId');
        var parentRoute = this.model.get('baseParentType') + '/' +
            this.model.get('baseParentId') + '/folder/' + folderId;
        var page = this;
        confirm({
            text: 'Are you sure you want to delete <b>' + this.model.escape('name') + '</b>?',
            yesText: 'Delete',
            escapedHtml: true,
            confirmCallback: _.bind(function () {
                this.model.on('g:deleted', function () {
                    router.navigate(parentRoute, {trigger: true});
                }).off('g:error').on('g:error', function () {
                    page.render();
                    events.trigger('g:alert', {
                        icon: 'cancel',
                        text: 'Failed to delete item.',
                        type: 'danger',
                        timeout: 4000
                    });
                }).destroy();
            }, this)
        });
    },

    render: function () {
        // Fetch the access level asynchronously and render once we have
        // it. TODO: load the page and adjust only the action menu once
        // the access level is fetched.
        this.model.getAccessLevel(_.bind(function (accessLevel) {
            this.accessLevel = accessLevel;
            this.$el.html(ItemPageTemplate({
                item: this.model,
                accessLevel: accessLevel,
                AccessType: AccessType,
                formatSize: formatSize,
                formatDate: formatDate,
                renderMarkdown: renderMarkdown,
                DATE_SECOND: DATE_SECOND
            }));

            this.$('.g-item-actions-button,.g-upload-into-item').tooltip({
                container: 'body',
                placement: 'left',
                animation: false,
                delay: {show: 100}
            });

            this.fileListWidget = new FileListWidget({
                el: this.$('.g-item-files-container'),
                item: this.model,
                fileEdit: this.fileEdit,
                upload: this.upload,
                parentView: this
            });
            this.fileListWidget.once('g:changed', function () {
                this.trigger('g:rendered');
            }, this);

            this.fileEdit = false;
            this.upload = false;

            this.metadataWidget = new MetadataWidget({
                el: this.$('.g-item-metadata'),
                item: this.model,
                accessLevel: accessLevel,
                parentView: this
            });

            this.model.getRootPath(_.bind(function (resp) {
                this.breadcrumbWidget = new ItemBreadcrumbWidget({
                    el: this.$('.g-item-breadcrumb-container'),
                    parentChain: resp,
                    parentView: this
                });
            }, this));

            if (this.edit) {
                this.editItem();
                this.edit = false;
            }
        }, this));

        return this;
    }
}, {
    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    fetchAndInit: function (itemId, params) {
        var item = new ItemModel();
        item.set({ _id: itemId }).on('g:fetched', function () {
            events.trigger('g:navigateTo', ItemView, _.extend({
                item: item
            }, params || {}));
        }, this).fetch();
    }
});

export default ItemView;
