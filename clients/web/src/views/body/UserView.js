(function () {

    /**
     * This view shows a single user's page.
     */
    girder.views.UserView = Backbone.View.extend({
        initialize: function (settings) {
            this.folderId = settings.folderId || null;

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
            else {
                console.error('Implement fetch then render user');
            }

            // This page should be re-rendered if the user logs in or out
            girder.events.on('g:login', this.userChanged, this);
        },

        render: function () {
            this.$el.html(jade.templates.userPage({
                user: this.model
            }));

            this.hierarchyWidget = new girder.views.HierarchyWidget({
                parentModel: this.folder || this.model,
                el: this.$('.g-user-hierarchy-container')
            });

            if (this.folder) {
                girder.router.navigate('user/' + this.model.get('_id') +
                    '/folder/' + this.folder.get('_id'));
            }
            else {
                girder.router.navigate('user/' + this.model.get('_id'));
            }

            return this;
        },

        userChanged: function () {
            // When the user changes, we should refresh the model to update the
            // accessLevel attribute on the viewed user, then re-render the page.
            this.model.off('g:fetched').on('g:fetched', function () {
                this.render();
            }, this).on('g:error', function () {
                // Current user no longer has read access to this user, so we
                // send them back to the user list page.
                girder.events.trigger('g:navigateTo', girder.views.UsersView);
            }, this).fetch();
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

    girder.router.route('user/:id/folder/:id', 'userFolder', function (userId, folderId) {
        _fetchAndInit(userId, {
            folderId: folderId
        });
    });

}) ();
