import $ from 'jquery';
import _ from 'underscore';

import PaginateWidget from '@girder/core/views/widgets/PaginateWidget';
import router from '@girder/core/router';
import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';
import UserCollection from '@girder/core/collections/UserCollection';
import View from '@girder/core/views/View';
import { AccessType } from '@girder/core/constants';
import { confirm } from '@girder/core/dialog';

import GroupInviteDialogTemplate from '@girder/core/templates/widgets/groupInviteDialog.pug';
import GroupMemberListTemplate from '@girder/core/templates/widgets/groupMemberList.pug';

import 'bootstrap/js/collapse';
import 'bootstrap/js/dropdown';
import 'bootstrap/js/transition';

import '@girder/core/utilities/jquery/girderModal';

var InviteUserDialog = View.extend({
    events: {
        'click .g-invite-as-member': function () {
            this._sendInvitation(AccessType.READ);
        },

        'click .g-invite-as-moderator': function () {
            this._sendInvitation(AccessType.WRITE);
        },

        'click .g-invite-as-admin': function () {
            this._sendInvitation(AccessType.ADMIN);
        },

        'click .g-add-as-member': function () {
            this._sendInvitation(AccessType.READ, true);
        },

        'click .g-add-as-moderator': function () {
            this._sendInvitation(AccessType.WRITE, true);
        },

        'click .g-add-as-admin': function () {
            this._sendInvitation(AccessType.ADMIN, true);
        }
    },

    initialize: function (settings) {
        this.group = settings.group;
        this.user = settings.user;
    },

    render: function () {
        this.$el.html(GroupInviteDialogTemplate({
            group: this.group,
            user: this.user,
            level: this.group.get('_accessLevel'),
            accessType: AccessType,
            mayAdd: this.group.mayAddMembers()
        })).girderModal(this);

        return this;
    },

    _sendInvitation: function (level, force) {
        this.$el.modal('hide');
        this.trigger('g:sendInvite', {
            user: this.user,
            group: this.group,
            level: level,
            force: force
        });
    }
});

/**
 * This view shows a list of members of a group.
 */
var GroupMembersWidget = View.extend({
    events: {
        'click a.g-member-name': function (e) {
            var model = this.membersColl.get(
                $(e.currentTarget).parents('li').attr('cid')
            );
            router.navigate('user/' + model.get('_id'), { trigger: true });
        },

        'click a.g-group-member-remove': function (e) {
            var user = this.membersColl.get(
                $(e.currentTarget).parents('li').attr('cid')
            );

            confirm({
                text: 'Are you sure you want to remove <b> ' + _.escape(user.name()) +
                    '</b> from this group?',
                escapedHtml: true,
                confirmCallback: () => {
                    this.trigger('g:removeMember', user);
                }
            });
        },

        'click .g-promote-moderator': function (e) {
            var cid = $(e.currentTarget).parents('.g-group-members>li')
                .attr('cid');
            var user = this.membersColl.get(cid);
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:moderatorAdded');
            }, this).promoteUser(user, AccessType.WRITE);
        },

        'click .g-promote-admin': function (e) {
            var cid = $(e.currentTarget).parents('.g-group-members>li')
                .attr('cid');
            var user = this.membersColl.get(cid);
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:adminAdded');
            }, this).promoteUser(user, AccessType.ADMIN);
        }
    },

    initialize: function (settings) {
        this.model = settings.group;
        this.modsAndAdmins = _.union(
            _.pluck(settings.admins, 'id'),
            _.pluck(settings.moderators, 'id')
        );
        this.membersColl = new UserCollection();
        this.membersColl.altUrl =
            'group/' + this.model.get('_id') + '/member';
        this.membersColl.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    render: function () {
        var members = [];
        for (var i = 0; i < this.membersColl.models.length; i += 1) {
            var member = this.membersColl.models[i];
            if ($.inArray(member.id, this.modsAndAdmins) < 0) {
                members.push(member);
            }
        }
        this.$el.html(GroupMemberListTemplate({
            group: this.model,
            members: members,
            level: this.model.get('_accessLevel'),
            accessType: AccessType
        }));

        new PaginateWidget({
            el: this.$('.g-member-pagination'),
            collection: this.membersColl,
            parentView: this
        }).render();

        this.userSearch = new SearchFieldWidget({
            el: this.$('.g-group-invite-container'),
            placeholder: 'Invite a user to join...',
            types: ['user'],
            parentView: this
        }).off().on('g:resultClicked', this._inviteUser, this).render();

        return this;
    },

    /**
     * When user searches and clicks a user, this method is called and a
     * dialog is opened allowing the user to select a role to invite into.
     */
    _inviteUser: function (user) {
        this.userSearch.resetState();

        new InviteUserDialog({
            el: $('#g-dialog-container'),
            group: this.model,
            user: user,
            parentView: this
        }).on('g:sendInvite', function (params) {
            this.trigger('g:sendInvite', params);
        }, this).render();
    }
});

export default GroupMembersWidget;
