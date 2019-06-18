import $ from 'jquery';
import _ from 'underscore';

import AccessWidget from '@girder/core/views/widgets/AccessWidget';
import CollectionModel from '@girder/core/models/CollectionModel';
import EditCollectionWidget from '@girder/core/views/widgets/EditCollectionWidget';
import FolderModel from '@girder/core/models/FolderModel';
import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import router from '@girder/core/router';
import View from '@girder/core/views/View';
import { AccessType } from '@girder/core/constants';
import { cancelRestRequests } from '@girder/core/rest';
import { confirm } from '@girder/core/dialog';
import { renderMarkdown, formatSize } from '@girder/core/misc';
import events from '@girder/core/events';

import CollectionPageTemplate from '@girder/core/templates/body/collectionPage.pug';

import '@girder/core/stylesheets/body/collectionPage.styl';

import 'bootstrap/js/dropdown';

/**
 * This view shows a single collection's page.
 */
var CollectionView = View.extend({
    events: {
        'click .g-edit-collection': 'editCollection',
        'click .g-collection-access-control': 'editAccess',
        'click .g-delete-collection': 'deleteConfirmation'
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');

        this.upload = settings.upload || false;
        this.access = settings.access || false;
        this.edit = settings.edit || false;
        this.folderAccess = settings.folderAccess || false;
        this.folderCreate = settings.folderCreate || false;
        this.folderEdit = settings.folderEdit || false;
        this.itemCreate = settings.itemCreate || false;

        // If collection model is already passed, there is no need to fetch.
        if (settings.collection) {
            this.model = settings.collection;

            if (settings.folderId) {
                this.folder = new FolderModel();
                this.folder.set({
                    _id: settings.folderId
                }).on('g:fetched', function () {
                    this.render();
                }, this).on('g:error', function () {
                    this.folder = null;
                    this.render();
                }, this).fetch();
            } else {
                this.render();
            }
        } else if (settings.id) {
            this.model = new CollectionModel();
            this.model.set('_id', settings.id);

            this.model.on('g:fetched', function () {
                this.render();
            }, this).fetch();
        }
    },

    editCollection: function () {
        var container = $('#g-dialog-container');

        if (!this.editCollectionWidget) {
            this.editCollectionWidget = new EditCollectionWidget({
                el: container,
                model: this.model,
                parentView: this
            }).on('g:saved', function () {
                this.render();
            }, this);
        }
        this.editCollectionWidget.render();
    },

    render: function () {
        this.$el.html(CollectionPageTemplate({
            collection: this.model,
            AccessType: AccessType,
            renderMarkdown: renderMarkdown
        }));

        if (!this.hierarchyWidget) {
            // The HierarchyWidget will self-render when instantiated
            this.hierarchyWidget = new HierarchyWidget({
                el: this.$('.g-collection-hierarchy-container'),
                parentModel: this.folder || this.model,
                upload: this.upload,
                folderAccess: this.folderAccess,
                folderEdit: this.folderEdit,
                folderCreate: this.folderCreate,
                itemCreate: this.itemCreate,
                parentView: this
            }).on('g:setCurrentModel', () => {
                // When a user descends into the hierarchy, hide the collection
                // actions list to avoid confusion.
                this.$('.g-collection-header .g-collection-actions-button').hide();
            });
        } else {
            this.hierarchyWidget
                .setElement(this.$('.g-collection-hierarchy-container'))
                .render();
        }

        this.upload = false;
        this.folderAccess = false;
        this.folderEdit = false;
        this.folderCreate = false;
        this.itemCreate = false;

        if (this.edit) {
            this.editCollection();
        } else if (this.access) {
            this.editAccess();
        }

        return this;
    },

    editAccess: function () {
        new AccessWidget({
            el: $('#g-dialog-container'),
            modelType: 'collection',
            model: this.model,
            parentView: this
        }).on('g:accessListSaved', function (params) {
            if (params.recurse) {
                this.hierarchyWidget.refreshFolderList();
            }
        }, this);
    },

    deleteConfirmation: function () {
        let params = {
            text: 'Are you sure you want to delete the collection <b>' +
                  this.model.escape('name') + this.model.escape('nFolders') + '</b>?',
            yesText: 'Delete',
            escapedHtml: true,
            confirmCallback: () => {
                this.model.on('g:deleted', function () {
                    events.trigger('g:alert', {
                        icon: 'ok',
                        text: 'Collection deleted.',
                        type: 'success',
                        timeout: 4000
                    });
                    router.navigate('collections', {trigger: true});
                }).destroy();
            }
        };
        if (this.model.get('nFolders') !== 0 || this.model.get('size') !== 0) {
            params = _.extend({
                additionalText: '<b>' + this.model.escape('name') + '</b>' +
                                ' contains <b>' + this.model.escape('nFolders') +
                                ' folders</b> taking up <b>' +
                                formatSize(parseInt(this.model.get('size'), 10)) + '</b>',
                msgConfirmation: true,
                name: this.model.escape('name')
            }, params);
        }
        confirm(params);
    }
}, {
    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    fetchAndInit: function (cid, params) {
        var collection = new CollectionModel();
        collection.set({ _id: cid }).on('g:fetched', function () {
            events.trigger('g:navigateTo', CollectionView, _.extend({
                collection: collection
            }, params || {}));
        }, this).fetch();
    }
});

export default CollectionView;
