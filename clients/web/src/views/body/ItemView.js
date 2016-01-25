(function () {
    /**
     * This view shows a single item's page.
     */
    girder.views.ItemView = girder.View.extend({
        events: {
            'click .g-edit-item': 'editItem',
            'click .g-delete-item': 'deleteItem',
            'click .g-upload-into-item': 'uploadIntoItem'
        },

        initialize: function (settings) {
            girder.cancelRestRequests('fetch');
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
            new girder.views.UploadWidget({
                el: $('#g-dialog-container'),
                parent: this.model,
                parentType: 'item',
                parentView: this
            }).on('g:uploadFinished', function () {
                girder.dialogs.handleClose('upload');
                this.upload = false;

                girder.events.trigger('g:alert', {
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
                this.editItemWidget = new girder.views.EditItemWidget({
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
            girder.confirm({
                text: 'Are you sure you want to delete <b>' + this.model.escape('name') + '</b>?',
                yesText: 'Delete',
                escapedHtml: true,
                confirmCallback: _.bind(function () {
                    this.model.destroy().on('g:deleted', function () {
                        girder.router.navigate(parentRoute, {trigger: true});
                    }).off('g:error').on('g:error', function () {
                        page.render();
                        girder.events.trigger('g:alert', {
                            icon: 'cancel',
                            text: 'Failed to delete item.',
                            type: 'danger',
                            timeout: 4000
                        });
                    });
                }, this)
            });
        },

        render: function () {
            // Fetch the access level asynchronously and render once we have
            // it. TODO: load the page and adjust only the action menu once
            // the access level is fetched.
            this.model.getAccessLevel(_.bind(function (accessLevel) {
                this.$el.html(girder.templates.itemPage({
                    item: this.model,
                    accessLevel: accessLevel,
                    girder: girder
                }));

                this.$('.g-item-actions-button,.g-upload-into-item').tooltip({
                    container: 'body',
                    placement: 'left',
                    animation: false,
                    delay: {show: 100}
                });

                this.fileListWidget = new girder.views.FileListWidget({
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

                this.metadataWidget = new girder.views.MetadataWidget({
                    el: this.$('.g-item-metadata'),
                    item: this.model,
                    accessLevel: accessLevel,
                    parentView: this
                });

                this.model.getRootPath(_.bind(function (resp) {
                    this.breadcrumbWidget = new girder.views.ItemBreadcrumbWidget({
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
    });

    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    var _fetchAndInit = function (itemId, params) {
        var item = new girder.models.ItemModel();
        item.set({
            _id: itemId
        }).on('g:fetched', function () {
            girder.events.trigger('g:navigateTo', girder.views.ItemView, _.extend({
                item: item
            }, params || {}));
        }, this).fetch();
    };

    girder.router.route('item/:id', 'item', function (itemId, params) {
        _fetchAndInit(itemId, {
            edit: params.dialog === 'itemedit',
            fileEdit: params.dialog === 'fileedit' ? params.dialogid : false,
            upload: params.dialog === 'upload' ? params.dialogid : false
        });
    });
}());
