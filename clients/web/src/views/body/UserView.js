(function () {
    /**
     * This view shows a single user's page.
     */
    girder.views.UserView = girder.View.extend({
        events: {
            'click a.g-edit-user': function () {
                var editUrl = 'useraccount/' + this.model.get('_id') + '/info';
                girder.router.navigate(editUrl, {trigger: true});
            },

            'click a.g-delete-user': function () {
                girder.confirm({
                    text: 'Are you sure you want to delete the user <b>' +
                          this.model.escape('login') + '</b>?',
                    yesText: 'Delete',
                    escapedHtml: true,
                    confirmCallback: _.bind(function () {
                        this.model.destroy().on('g:deleted', function () {
                            girder.router.navigate('users', {trigger: true});
                        });
                    }, this)
                });
            },

            'click a.g-approve-user': function () {
                this._setAndSave(
                    {status: 'enabled'}, 'Approved user account.');
            },

            'click a.g-disable-user': function () {
                this._setAndSave(
                    {status: 'disabled'}, 'Disabled user account.');
            },

            'click a.g-enable-user': function () {
                this._setAndSave(
                    {status: 'enabled'}, 'Enabled user account.');
            }
        },

        initialize: function (settings) {
            girder.cancelRestRequests('fetch');
            this.folderId = settings.folderId || null;
            this.upload = settings.upload || false;
            this.folderAccess = settings.folderAccess || false;
            this.folderCreate = settings.folderCreate || false;
            this.folderEdit = settings.folderEdit || false;
            this.itemCreate = settings.itemCreate || false;

            if (settings.user) {
                this.model = settings.user;

                if (settings.folderId) {
                    this.folder = new girder.models.FolderModel();
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
                this.model = new girder.models.UserModel();
                this.model.set('_id', settings.id);

                this.model.on('g:fetched', function () {
                    this._createHierarchyWidget();
                    this.render();
                }, this).fetch();
            }
        },

        _createHierarchyWidget: function () {
            this.hierarchyWidget = new girder.views.HierarchyWidget({
                parentModel: this.folder || this.model,
                upload: this.upload,
                folderAccess: this.folderAccess,
                folderEdit: this.folderEdit,
                folderCreate: this.folderCreate,
                itemCreate: this.itemCreate,
                parentView: this
            });
        },

        render: function () {
            this.$el.html(girder.templates.userPage({
                user: this.model,
                girder: girder
            }));

            this.hierarchyWidget.setElement(this.$('.g-user-hierarchy-container')).render();

            this.upload = false;
            this.folderAccess = false;
            this.folderEdit = false;
            this.folderCreate = false;
            this.itemCreate = false;

            return this;
        },

        _setAndSave: function (data, message) {
            this.model.set(data);
            this.model.off('g:saved').on('g:saved', function () {
                girder.events.trigger('g:alert', {
                    icon: 'ok',
                    text: message,
                    type: 'success',
                    timeout: 4000
                });
                this.render();
            }, this).off('g:error').on('g:error', function (err) {
                girder.events.trigger('g:alert', {
                    icon: 'cancel',
                    text: err.responseJSON.message,
                    type: 'danger'
                });
            }).save();
        }
    });

    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    var _fetchAndInit = function (userId, params) {
        var user = new girder.models.UserModel();
        user.set({
            _id: userId
        }).on('g:fetched', function () {
            girder.events.trigger('g:navigateTo', girder.views.UserView, _.extend({
                user: user
            }, params || {}));
        }, this).on('g:error', function () {
            girder.events.trigger('g:navigateTo', girder.views.UsersView);
        }, this).fetch();
    };

    girder.router.route('user/:id', 'user', function (userId, params) {
        _fetchAndInit(userId, {
            folderCreate: params.dialog === 'foldercreate',
            dialog: params.dialog
        });
    });

    girder.router.route('user/:id/folder/:id', 'userFolder', function (userId, folderId, params) {
        _fetchAndInit(userId, {
            folderId: folderId,
            upload: params.dialog === 'upload',
            folderAccess: params.dialog === 'folderaccess',
            folderCreate: params.dialog === 'foldercreate',
            folderEdit: params.dialog === 'folderedit',
            itemCreate: params.dialog === 'itemcreate'
        });
    });
}());
