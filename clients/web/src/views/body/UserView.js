(function () {

    /**
     * This view shows a single user's page.
     */
    girder.views.UserView = girder.View.extend({
        events: {

            'click a.g-edit-user': function (event) {
                var editUrl = 'useraccount/' + this.model.get('_id') + '/info';
                girder.router.navigate(editUrl, {trigger: true});
            },

            'click a.g-delete-user': function (event) {
                girder.confirm({
                    text: 'Are you sure you want to delete <b>' +
                          this.model.get('login') + '</b>?',
                    yesText: 'Delete',
                    confirmCallback: _.bind(function () {
                        this.model.destroy().on('g:deleted', function () {
                            girder.router.navigate('users', {trigger: true});
                        });
                    }, this)
                });
            }
        },

        initialize: function (settings) {
            this.folderId = settings.folderId || null;
            this.upload = settings.upload || false;
            this.folderAccess = settings.folderAccess || false;
            this.folderEdit = settings.folderEdit || false;

            if (settings.user) {
                this.model = settings.user;

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
                this.model = new girder.models.UserModel();
                this.model.set('_id', settings.id);

                this.model.on('g:fetched', function () {
                    this.render();
                }, this).fetch();
            }
        },

        render: function () {
            this.$el.html(jade.templates.userPage({
                user: this.model,
                girder: girder
            }));

            this.hierarchyWidget = new girder.views.HierarchyWidget({
                parentModel: this.folder || this.model,
                el: this.$('.g-user-hierarchy-container'),
                upload: this.upload,
                edit: this.folderEdit,
                access: this.folderAccess
            });

            return this;
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

    girder.router.route('user/:id', 'user', function (userId) {
        _fetchAndInit(userId);
    });

    girder.router.route('user/:id/folder/:id', 'userFolder', function (userId, folderId, params) {
        _fetchAndInit(userId, {
            folderId: folderId,
            upload: params.dialog === 'upload',
            folderAccess: params.dialog === 'folderaccess',
            folderEdit: params.dialog === 'folderedit'
        });
    });

}) ();
