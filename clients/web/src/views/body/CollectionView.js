(function () {
    /**
     * This view shows a single collection's page.
     */
    girder.views.CollectionView = girder.View.extend({
        events: {
            'click .g-edit-collection': 'editCollection',
            'click .g-collection-access-control': 'editAccess'
        },

        initialize: function (settings) {

            this.upload = settings.upload || false;
            this.access = settings.access || false;
            this.folderAccess = settings.folderAccess || false;
            this.folderEdit = settings.folderEdit || false;
            this.edit = settings.edit || false;

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
            }
            else if (settings.id) {
                this.model = new girder.models.CollectionModel();
                this.model.set('_id', settings.id);

                this.model.on('g:fetched', function () {
                    this.render();
                }, this).fetch();
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
                upload: this.upload,
                access: this.folderAccess,
                edit: this.folderEdit,
                el: this.$('.g-collection-hierarchy-container')
            });

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
            girder.router.navigate('/collections', {trigger: true});
        }, this).fetch();
    };

    girder.router.route('collection/:id', 'collectionAccess', function (collectionId, params) {
        _fetchAndInit(collectionId, {
            access: params.dialog === 'access',
            edit: params.dialog === 'edit'
        });
    });

    girder.router.route('collection/:id/folder/:id', 'collectionFolder',
        function (collectionId, folderId, params) {
            _fetchAndInit(collectionId, {
                folderId: folderId,
                upload: params.dialog === 'upload',
                access: params.dialog === 'access',
                folderAccess: params.dialog === 'folderaccess',
                edit: params.dialog === 'edit',
                folderEdit: params.dialog === 'folderedit'
            });
        });

}) ();
