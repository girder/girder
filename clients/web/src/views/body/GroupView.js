/**
 * This view shows a single group's page.
 */
girder.views.GroupView = Backbone.View.extend({
    events: {
        'click .g-edit-group': 'editGroup',
        'click .g-group-invite': 'invitationDialog',
        'click .g-group-join': 'joinGroup',
        'click .g-group-leave': 'leaveGroup',
        'click .g-group-delete': 'deleteGroup'
    },

    initialize: function (settings) {
        // If group model is already passed, there is no need to fetch.
        if (settings.group) {
            this.model = settings.group;
            this.render();
        }
        else if (settings.id) {
            this.model = new girder.models.GroupModel();
            this.model.set('_id', settings.id);

            this.model.on('g:fetched', function () {
                this.render();
            }, this).fetch();
        }
        // This page should be re-rendered if the user logs in or out
        girder.events.on('g:login', this.userChanged, this);
    },

    editGroup: function () {
        var container = $('#g-dialog-container');

        if (!this.editGroupWidget) {
            this.editGroupWidget = new girder.views.EditGroupWidget({
                el: container,
                model: this.model
            }).off('g:saved').on('g:saved', function (group) {
                this.render();
            }, this);
        }
        this.editGroupWidget.render();
    },

    deleteGroup: function () {
        var view = this;
        girder.confirm({
            text: 'Are you sure you want to delete the group <b>' +
            view.model.get('name') + '</b>?',
            confirmCallback: function () {
                view.model.on('g:deleted', function () {
                    girder.events.trigger('g:navigateTo',
                        girder.views.GroupsView);
                }).destroy();
            }
        });
    },

    render: function () {
        this.isMember = false;
        this.isInvited = false;

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
        }
        this.$el.html(jade.templates.groupPage({
            group: this.model,
            girder: girder,
            isInvited: this.isInvited,
            isMember: this.isMember
        }));

        this.membersWidget = new girder.views.GroupMembersWidget({
            el: this.$('.g-group-members-container'),
            group: this.model
        }).off().on('g:sendInvite', function (params) {
            this.model.off('g:invited').on('g:invited', function () {
                this.render();
            }, this).off('g:error').on('g:error', function (err) {
                // TODO don't alert, show something useful
                alert(err.responseJSON.message);
            }, this).sendInvitation(params.user.id, params.level);
        }, this).on('g:removeMember', this.removeMember, this);

        this.$('.g-group-actions-button').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        girder.router.navigate('group/' + this.model.get('_id'));

        return this;
    },

    userChanged: function () {
        // When the user changes, we should refresh the model to update the
        // _accessLevel attribute on the viewed group, then re-render the page.
        this.model.off('g:fetched').on('g:fetched', function () {
            this.render();
        }, this).on('g:error', function () {
            // Current user no longer has read access to this group, so we
            // send them back to the group list page.
            girder.events.trigger('g:navigateTo', girder.views.GroupsView);
        }, this).fetch();
    },

    joinGroup: function () {
        this.model.off('g:joined').on('g:joined', function () {
            this.render();
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
        this.model.off('g:removed').on('g:removed', function () {
            this.render();
        }, this).removeMember(user.get('_id'));
    }
});

girder.router.route('group/:id', 'group', function (id) {
    // Fetch the group by id, then render the view.
    var group = new girder.models.GroupModel();
    group.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.GroupView, {
            group: group
        }, group);
    }, this).on('g:error', function () {
        girder.events.trigger('g:navigateTo', girder.views.GroupsView);
    }, this).fetch();
});
