var _               = require('underscore');
var girder          = require('girder/init');
var Events          = require('girder/events');
var FolderModel     = require('girder/models/FolderModel');
var UserModel       = require('girder/models/UserModel');
var View            = require('girder/view');
var HierarchyWidget = require('girder/views/widgets/HierarchyWidget');
var MiscFunctions   = require('girder/utilities/MiscFunctions');
var UsersView       = require('girder/views/body/UsersView');

// (function () {
    /**
     * This view shows a single user's page.
     */
    var UserView = View.extend({
        events: {
            'click a.g-edit-user': function () {
                var editUrl = 'useraccount/' + this.model.get('_id') + '/info';
                girder.router.navigate(editUrl, {trigger: true});
            },

            'click a.g-delete-user': function () {
                MiscFunctions.confirm({
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
            }
        },

        initialize: function (settings) {
            MiscFunctions.cancelRestRequests('fetch');
            this.folderId = settings.folderId || null;
            this.upload = settings.upload || false;
            this.folderAccess = settings.folderAccess || false;
            this.folderCreate = settings.folderCreate || false;
            this.folderEdit = settings.folderEdit || false;
            this.itemCreate = settings.itemCreate || false;

            if (settings.user) {
                this.model = settings.user;

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
                this.model = new UserModel();
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
        }
    });

    module.exports = UserView;

    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    var _fetchAndInit = function (userId, params) {
        var user = new UserModel();
        user.set({
            _id: userId
        }).on('g:fetched', function () {
            Events.trigger('g:navigateTo', UserView, _.extend({
                user: user
            }, params || {}));
        }, this).on('g:error', function () {
            Events.trigger('g:navigateTo', UsersView);
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
// }());
