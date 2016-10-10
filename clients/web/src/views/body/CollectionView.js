import $ from 'jquery';
import _ from 'underscore';

import AccessWidget from 'girder/views/widgets/AccessWidget';
import CollectionModel from 'girder/models/CollectionModel';
import EditCollectionWidget from 'girder/views/widgets/EditCollectionWidget';
import FolderModel from 'girder/models/FolderModel';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import router from 'girder/router';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { cancelRestRequests } from 'girder/rest';
import { confirm } from 'girder/dialog';
import events from 'girder/events';

import CollectionPageTemplate from 'girder/templates/body/collectionPage.pug';

import 'girder/stylesheets/body/collectionPage.styl';

import 'bootstrap/js/dropdown';
import 'bootstrap/js/tooltip';

/**
 * This view shows a single collection's page.
 */
var CollectionView = View.extend({
    events: {
        'click .g-edit-collection': 'editCollection',
        'click .g-collection-access-control': 'editAccess',
        'click .g-delete-collection': function () {
            confirm({
                text: 'Are you sure you want to delete the collection <b>' +
                      this.model.escape('name') + '</b>?',
                yesText: 'Delete',
                escapedHtml: true,
                confirmCallback: _.bind(function () {
                    this.model.on('g:deleted', function () {
                        events.trigger('g:alert', {
                            icon: 'ok',
                            text: 'Collection deleted.',
                            type: 'success',
                            timeout: 4000
                        });
                        router.navigate('collections', {trigger: true});
                    }).destroy();
                }, this)
            });
        }
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
                    this._createHierarchyWidget();
                    this.render();
                }, this).on('g:error', function () {
                    this.folder = null;
                    this._createHierarchyWidget();
                    this.render();
                }, this).fetch();
            } else {
                this._createHierarchyWidget();
                this.render();
            }
        } else if (settings.id) {
            this.model = new CollectionModel();
            this.model.set('_id', settings.id);

            this.model.on('g:fetched', function () {
                this._createHierarchyWidget();
                this.render();
            }, this).fetch();
        }
    },

    _createHierarchyWidget: function () {
        this.hierarchyWidget = new HierarchyWidget({
            parentModel: this.folder || this.model,
            upload: this.upload,
            folderAccess: this.folderAccess,
            folderEdit: this.folderEdit,
            folderCreate: this.folderCreate,
            itemCreate: this.itemCreate,
            parentView: this
        }).on('g:setCurrentModel', function () {
            // When a user descends into the hierarchy, hide the collection
            // actions list to avoid confusion.
            this.$('.g-collection-header .g-collection-actions-button').hide();
        }, this);
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
            AccessType: AccessType
        }));

        this.hierarchyWidget.setElement(
            this.$('.g-collection-hierarchy-container')).render();

        this.upload = false;
        this.folderAccess = false;
        this.folderEdit = false;
        this.folderCreate = false;
        this.itemCreate = false;

        this.$('.g-collection-actions-button').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

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
