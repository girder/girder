(function () {
    /**
     * This view shows a single group's page.
     */
    girder.views.GroupView = girder.View.extend({
        events: {
            'click .g-edit-group': 'editGroup',
            'click .g-group-join': 'joinGroup',
            'click .g-group-leave': 'leaveGroup',
            'click .g-group-delete': 'deleteGroup',
            'click .g-group-request-invite': 'requestInvitation',
            'click .g-group-request-accept': 'acceptMembershipRequest',
            'click .g-group-request-deny': 'denyMembershipRequest',

            'click #g-group-tab-pending a.g-member-name': function (e) {
                var userId = $(e.currentTarget).parents('li').attr('userid');
                girder.router.navigate('user/' + userId, {trigger: true});
            }
        },

        initialize: function (settings) {
            girder.cancelRestRequests('fetch');
            this.tab = settings.tab || 'roles';
            this.edit = settings.edit || false;

            // If group model is already passed, there is no need to fetch.
            if (settings.group) {
                this.model = settings.group;
                this.model.on('g:accessFetched', function () {
                    this.render();
                }, this).fetchAccess();
            } else if (settings.id) {
                this.model = new girder.models.GroupModel();
                this.model.set('_id', settings.id);

                this.model.on('g:fetched', function () {
                    this.model.on('g:accessFetched', function () {
                        this.render();
                    }, this).fetchAccess();
                }, this).fetch();
            }
        },

        editGroup: function () {
            var container = $('#g-dialog-container');

            if (!this.editGroupWidget) {
                this.editGroupWidget = new girder.views.EditGroupWidget({
                    el: container,
                    model: this.model,
                    parentView: this
                }).off('g:saved').on('g:saved', function () {
                    this.render();
                }, this);
            }
            this.editGroupWidget.render();
        },

        deleteGroup: function () {
            var view = this;
            girder.confirm({
                text: 'Are you sure you want to delete the group <b>' +
                    view.model.escape('name') + '</b>?',
                escapedHtml: true,
                confirmCallback: function () {
                    view.model.on('g:deleted', function () {
                        girder.router.navigate('groups', {trigger: true});
                    }).destroy();
                }
            });
        },

        render: function () {
            this.isMember = false;
            this.isInvited = false;
            this.isRequested = false;
            this.isModerator = false;
            this.isAdmin = false;

            if (girder.currentUser) {
                _.every(girder.currentUser.get('groups'), function (groupId) {
                    if (groupId === this.model.get('_id')) {
                        this.isMember = true;
                        return false; // 'break;'
                    }
                    return true;
                }, this);

                _.every(girder.currentUser.get('groupInvites'), function (inv) {
                    if (inv.groupId === this.model.get('_id')) {
                        this.isInvited = true;
                        return false; // 'break;'
                    }
                    return true;
                }, this);

                _.every(this.model.get('requests') || [], function (user) {
                    if (user.id === girder.currentUser.get('_id')) {
                        this.isRequested = true;
                        return false; // 'break;'
                    }
                    return true;
                }, this);
            }

            if (this.isMember) {
                _.every(this.model.get('access').users || [], function (access) {
                    if (access.id === girder.currentUser.get('_id')) {
                        if (access.level === girder.AccessType.WRITE) {
                            this.isModerator = true;
                        } else if (access.level === girder.AccessType.ADMIN) {
                            this.isAdmin = true;
                        }
                        return false; // 'break';
                    }
                    return true;
                }, this);
            }
            this.$el.html(girder.templates.groupPage({
                group: this.model,
                girder: girder,
                isInvited: this.isInvited,
                isRequested: this.isRequested,
                isMember: this.isMember,
                isModerator: this.isModerator,
                isAdmin: this.isAdmin
            }));

            if (this.invitees) {
                this._renderInvitesWidget();
            } else {
                var container = this.$('.g-group-invites-body');
                new girder.views.LoadingAnimation({
                    el: container,
                    parentView: this
                }).render();

                this.invitees = new girder.collections.UserCollection();
                this.invitees.altUrl =
                    'group/' + this.model.get('_id') + '/invitation';
                var view = this;
                this.invitees.on('g:changed', function () {
                    this._renderInvitesWidget();
                    view.updatePendingStatus();
                }, this).fetch();
            }

            this._updateRolesLists();

            this.$('.g-group-actions-button,a[title]').tooltip({
                container: this.$el,
                placement: 'left',
                animation: false,
                delay: {show: 100}
            });
            this.$('.g-group-list-header[title]').tooltip({
                container: this.$el,
                placement: 'top',
                animation: false,
                delay: {show: 100}
            });

            girder.router.navigate('group/' + this.model.get('_id') + '/' +
                                   this.tab, {replace: true});

            if (this.edit) {
                if (this.model.get('_accessLevel') >= girder.AccessType.ADMIN) {
                    this.editGroup();
                }
                this.edit = false;
            }

            _.each($('.g-group-tabs>li>a'), function (el) {
                var tabLink = $(el);
                var view = this;
                tabLink.tab().on('shown.bs.tab', function (e) {
                    view.tab = $(e.currentTarget).attr('name');
                    girder.router.navigate('group/' + view.model.get('_id') + '/' + view.tab);
                });

                if (tabLink.attr('name') === this.tab) {
                    tabLink.tab('show');
                }
            }, this);

            return this;
        },

        _renderInvitesWidget: function () {
            new girder.views.GroupInvitesWidget({
                el: this.$('.g-group-invites-body'),
                invitees: this.invitees,
                group: this.model,
                parentView: this
            }).render();
            this.updatePendingStatus();
        },

        updatePendingStatus: function () {
            var count = this.invitees.length +
                this.model.get('requests').length;
            $('#g-group-tab-pending-status').text(' (' + count + ')');
        },

        joinGroup: function () {
            this.model.off('g:joined').on('g:joined', function () {
                this.invitees.fetch(null, true);
            }, this).joinGroup();
        },

        leaveGroup: function () {
            var view = this;
            girder.confirm({
                text: 'Are you sure you want to leave this group?',
                confirmCallback: function () {
                    view.model.off('g:removed').on('g:removed', function () {
                        view.render();
                    }).removeMember(girder.currentUser.get('_id'));
                }
            });
        },

        removeMember: function (user) {
            var id = user;
            if ($.type(user) !== 'string') {
                id = user.get('_id');
            }
            this.model.off('g:removed').on('g:removed', function () {
                this.render();
            }, this).removeMember(id);
        },

        requestInvitation: function () {
            this.model.off('g:inviteRequested').on('g:inviteRequested', function () {
                this.render();
            }, this).requestInvitation();
        },

        acceptMembershipRequest: function (e) {
            var userId = $(e.currentTarget).parents('li').attr('userid');
            this.model.off('g:invited').on('g:invited', this.render, this)
                      .sendInvitation(userId, girder.AccessType.READ, true);
        },

        denyMembershipRequest: function (e) {
            var userId = $(e.currentTarget).parents('li').attr('userid');
            this.model.off('g:removed').on('g:removed', this.render, this)
                      .removeMember(userId);
        },

        _updateRolesLists: function () {
            var mods = [],
                admins = [];

            _.each(this.model.get('access').users, function (userAccess) {
                if (userAccess.level === girder.AccessType.WRITE) {
                    mods.push(userAccess);
                } else if (userAccess.level === girder.AccessType.ADMIN) {
                    admins.push(userAccess);
                }
            }, this);

            this.adminsWidget = new girder.views.GroupAdminsWidget({
                el: this.$('.g-group-admins-container'),
                group: this.model,
                admins: admins,
                parentView: this
            }).off().on('g:demoteUser', function (userId) {
                this.model.off('g:demoted').on('g:demoted', this.render, this)
                          .demoteUser(userId, girder.AccessType.ADMIN);
            }, this).on('g:removeMember', this.removeMember, this)
                    .on('g:moderatorAdded', this.render, this)
                    .render();

            this.modsWidget = new girder.views.GroupModsWidget({
                el: this.$('.g-group-mods-container'),
                group: this.model,
                moderators: mods,
                parentView: this
            }).on('g:demoteUser', function (userId) {
                this.model.off('g:demoted').on('g:demoted', this.render, this)
                          .demoteUser(userId, girder.AccessType.WRITE);
            }, this).on('g:removeMember', this.removeMember, this)
                    .on('g:adminAdded', this.render, this)
                    .render();

            this.membersWidget = new girder.views.GroupMembersWidget({
                el: this.$('.g-group-members-container'),
                group: this.model,
                admins: admins,
                moderators: mods,
                parentView: this
            }).on('g:sendInvite', function (params) {
                var opts = {
                    force: params.force || false
                };
                this.model.off('g:invited').on('g:invited', function () {
                    this.invitees.fetch(null, true);
                    if (params.force) {
                        this.model.fetchAccess();
                    }
                }, this).off('g:error').on('g:error', function (err) {
                    // TODO don't alert, show something useful
                    alert(err.responseJSON.message);
                }, this).sendInvitation(params.user.id, params.level, false, opts);
            }, this).on('g:removeMember', this.removeMember, this)
                    .on('g:moderatorAdded', this.render, this)
                    .on('g:adminAdded', this.render, this);
        }
    });

    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    var _fetchAndInit = function (groupId, params) {
        var group = new girder.models.GroupModel();
        group.set({
            _id: groupId
        }).once('g:fetched', function () {
            girder.events.trigger('g:navigateTo', girder.views.GroupView, _.extend({
                group: group
            }, params || {}));
        }, this).fetch();
    };

    girder.router.route('group/:id', 'groupView', function (groupId, params) {
        _fetchAndInit(groupId, {
            edit: params.dialog === 'edit'
        });
    });

    girder.router.route('group/:id/:tab', 'groupView', function (groupId, tab, params) {
        _fetchAndInit(groupId, {
            edit: params.dialog === 'edit',
            tab: tab
        });
    });
}());
