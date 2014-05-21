/**
 * This view shows a list of members of a group.
 */
girder.views.GroupMembersWidget = girder.View.extend({
    events: {
        'click a.g-member-name': function (e) {
            var model = this.membersColl.get(
                $(e.currentTarget).parents('li').attr('cid'));
            girder.events.trigger('g:navigateTo', girder.views.UserView, {
                id: model.get('_id')
            });
        },

        'click a.g-group-member-remove': function (e) {
            var view = this;
            var user = this.membersColl.get(
                $(e.currentTarget).parents('li').attr('cid'));

            girder.confirm({
                text: 'Are you sure you want to remove <b> ' + user.name() +
                '</b> from this group?',
                confirmCallback: function () {
                    view.trigger('g:removeMember', user);
                }
            });
        },

        'click .g-promote-moderator': function (e) {
            var cid = $(e.currentTarget).parents('.g-group-members>li')
                                        .attr('cid');
            var user = this.membersColl.get(cid);
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:moderatorAdded');
            }, this).promoteUser(user, girder.AccessType.WRITE);
        },

        'click .g-promote-admin': function (e) {
            var cid = $(e.currentTarget).parents('.g-group-members>li')
                                        .attr('cid');
            var user = this.membersColl.get(cid);
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:adminAdded');
            }, this).promoteUser(user, girder.AccessType.ADMIN);
        }
    },

    initialize: function (settings) {
        this.model = settings.group;
        this.membersColl = new girder.collections.UserCollection();
        this.membersColl.altUrl =
            'group/' + this.model.get('_id') + '/member';
        this.membersColl.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    render: function () {
        this.$el.html(jade.templates.groupMemberList({
            group: this.model,
            members: this.membersColl.models,
            level: this.model.get('_accessLevel'),
            accessType: girder.AccessType
        }));

        new girder.views.PaginateWidget({
            el: this.$('.g-member-pagination'),
            collection: this.membersColl
        }).render();

        this.userSearch = new girder.views.SearchFieldWidget({
            el: this.$('.g-group-invite-container'),
            placeholder: 'Invite a user to join...',
            types: ['user']
        }).off().on('g:resultClicked', this._inviteUser, this).render();

        this.$('.g-group-member-remove,.g-group-member-promote').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    },

    /**
     * When user searches and clicks a user, this method is called and a
     * dialog is opened allowing the user to select a role to invite into.
     */
    _inviteUser: function (user) {
        this.userSearch.resetState();

        new girder.views.InviteUserDialog({
            el: $('#g-dialog-container'),
            group: this.model,
            user: user
        }).on('g:sendInvite', function (params) {
            this.trigger('g:sendInvite', params);
        }, this).render();
    }
});

girder.views.InviteUserDialog = girder.View.extend({
    events: {
        'click .g-invite-as-member': function () {
            this.$el.modal('hide');
            this.trigger('g:sendInvite', {
                user: this.user,
                group: this.group,
                level: girder.AccessType.READ
            });
        },

        'click .g-invite-as-moderator': function () {
            this.$el.modal('hide');
            this.trigger('g:sendInvite', {
                user: this.user,
                group: this.group,
                level: girder.AccessType.WRITE
            });
        },

        'click .g-invite-as-admin': function () {
            this.$el.modal('hide');
            this.trigger('g:sendInvite', {
                user: this.user,
                group: this.group,
                level: girder.AccessType.ADMIN
            });
        }
    },

    initialize: function (settings) {
        this.group = settings.group;
        this.user = settings.user;
    },

    render: function () {
        this.$el.html(jade.templates.groupInviteDialog({
            group: this.group,
            user: this.user,
            level: this.group.get('_accessLevel'),
            accessType: girder.AccessType
        })).girderModal(this);

        return this;
    }
});
