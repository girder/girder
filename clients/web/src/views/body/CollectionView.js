(function () {
    /**
     * This view shows a single collection's page.
     */
    girder.views.CollectionView = Backbone.View.extend({
        events: {
            'click .g-edit-collection': 'editCollection',
            'click .g-collection-access-control': 'editAccess'
        },

        initialize: function (settings) {
            // If collection model is already passed, there is no need to fetch.
            if (settings.collection) {
                this.model = settings.collection;

                if (settings.folderId) {
                    this.folder = new girder.models.FolderModel();
                    this.folder.set({
                        _id: settings.folderId
                    }).on('g:fetched', function () {
                        this.render();
                    }, this).on('g:error', function () {
                        this.folder = null;
                        this.render();
                    }, this).fetch();
                }
                else {
                    this.render();
                }

                // This page should be re-rendered if the user logs in or out
                girder.events.on('g:login', this.userChanged, this);
            }
            else {
                console.error('Implement fetch then render collection');
            }

        },

        editCollection: function () {
            var container = $('#g-dialog-container');

            if (!this.editCollectionWidget) {
                this.editCollectionWidget = new girder.views.EditCollectionWidget({
                    el: container,
                    model: this.model
                }).off('g:saved').on('g:saved', function (collection) {
                    this.render();
                }, this);
            }
            this.editCollectionWidget.render();
        },

        render: function () {
            this.$el.html(jade.templates.collectionPage({
                collection: this.model,
                girder: girder
            }));

            this.hierarchyWidget = new girder.views.HierarchyWidget({
                parentModel: this.folder || this.model,
                el: this.$('.g-collection-hierarchy-container')
            });

            this.$('.g-collection-actions-button').tooltip({
                container: 'body',
                placement: 'left',
                animation: false,
                delay: {show: 100}
            });

            if (this.folder) {
                girder.router.navigate('collection/' + this.model.get('_id') + '/folder/'
                    + this.folder.get('_id'));
            }
            else {
                girder.router.navigate('collection/' + this.model.get('_id'));
            }

            return this;
        },

        userChanged: function () {
            // When the user changes, we should refresh the model to update the
            // _accessLevel attribute on the viewed collection, then re-render the
            // page.
            this.model.off('g:fetched').on('g:fetched', function () {
                this.render();
            }, this).on('g:error', function () {
                // Current user no longer has read access to this user, so we
                // send them back to the user list page.
                girder.events.trigger('g:navigateTo',
                    girder.views.CollectionsView);
            }, this).fetch();
        },

        editAccess: function () {
            new girder.views.AccessWidget({
                el: $('#g-dialog-container'),
                modelType: 'collection',
                model: this.model
            }).on('g:saved', function (collection) {
                // need to do anything?
            }, this);
        }

    });

    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    var _fetchAndInit = function (collectionId, params) {
        var collection = new girder.models.CollectionModel();
        collection.set({
            _id: collectionId
        }).on('g:fetched', function () {
            girder.events.trigger('g:navigateTo', girder.views.CollectionView, _.extend({
                collection: collection
            }, params || {}));
        }, this).on('g:error', function () {
            girder.events.trigger('g:navigateTo', girder.views.CollectionsView);
        }, this).fetch();
    };

    girder.router.route('collection/:id', 'collection', function (collectionId) {
        _fetchAndInit(collectionId);
    });

    girder.router.route('collection/:id/folder/:id', 'collectionFolder',
        function (collectionId, folderId) {
            _fetchAndInit(collectionId, {
                folderId: folderId
            });
        });

}) ();
