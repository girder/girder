import $ from 'jquery';
import _ from 'underscore';

import EditGroupWidget from '@girder/core/views/widgets/EditGroupWidget';
import GroupAdminsWidget from '@girder/core/views/widgets/GroupAdminsWidget';
import GroupInvitesWidget from '@girder/core/views/widgets/GroupInvitesWidget';
import GroupMembersWidget from '@girder/core/views/widgets/GroupMembersWidget';
import GroupModel from '@girder/core/models/GroupModel';
import GroupModsWidget from '@girder/core/views/widgets/GroupModsWidget';
import LoadingAnimation from '@girder/core/views/widgets/LoadingAnimation';
import router from '@girder/core/router';
import UserCollection from '@girder/core/collections/UserCollection';
import View from '@girder/core/views/View';
import { AccessType } from '@girder/core/constants';
import { cancelRestRequests } from '@girder/core/rest';
import { confirm } from '@girder/core/dialog';
import events from '@girder/core/events';
import { getCurrentUser } from '@girder/core/auth';

import GroupPageTemplate from '@girder/core/templates/body/groupPage.pug';

import '@girder/core/stylesheets/body/groupPage.styl';

import 'bootstrap/js/dropdown';
import 'bootstrap/js/tab';

/**
 * This view shows a single group's page.
 */
var GroupView = View.extend({
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
            router.navigate('user/' + userId, { trigger: true });
        }
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.tab = settings.tab || 'roles';
        this.edit = settings.edit || false;

        // If group model is already passed, there is no need to fetch.
        if (settings.group) {
            this.model = settings.group;
            this.model.on('g:accessFetched', function () {
                this.render();
            }, this).fetchAccess();
        } else if (settings.id) {
            this.model = new GroupModel();
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
            this.editGroupWidget = new EditGroupWidget({
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
        confirm({
            text: 'Are you sure you want to delete the group <b>' +
                this.model.escape('name') + '</b>?',
            escapedHtml: true,
            confirmCallback: () => {
                this.model.on('g:deleted', function () {
                    router.navigate('groups', { trigger: true });
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

        if (getCurrentUser()) {
            _.every(getCurrentUser().get('groups'), function (groupId) {
                if (groupId === this.model.get('_id')) {
                    this.isMember = true;
                    return false; // 'break;'
                }
                return true;
            }, this);

            _.every(getCurrentUser().get('groupInvites'), function (inv) {
                if (inv.groupId === this.model.get('_id')) {
                    this.isInvited = true;
                    return false; // 'break;'
                }
                return true;
            }, this);

            _.every(this.model.get('requests') || [], function (user) {
                if (user.id === getCurrentUser().get('_id')) {
                    this.isRequested = true;
                    return false; // 'break;'
                }
                return true;
            }, this);
        }

        if (this.isMember) {
            _.every(this.model.get('access').users || [], function (access) {
                if (access.id === getCurrentUser().get('_id')) {
                    if (access.level === AccessType.WRITE) {
                        this.isModerator = true;
                    } else if (access.level === AccessType.ADMIN) {
                        this.isAdmin = true;
                    }
                    return false; // 'break';
                }
                return true;
            }, this);
        }
        this.$el.html(GroupPageTemplate({
            group: this.model,
            getCurrentUser: getCurrentUser,
            AccessType: AccessType,
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
            new LoadingAnimation({
                el: container,
                parentView: this
            }).render();

            this.invitees = new UserCollection();
            this.invitees.altUrl =
                'group/' + this.model.get('_id') + '/invitation';
            this.invitees.on('g:changed', () => {
                this._renderInvitesWidget();
                this.updatePendingStatus();
            }, this).fetch();
        }

        this._updateRolesLists();

        router.navigate('group/' + this.model.get('_id') + '/' +
                               this.tab, { replace: true });

        if (this.edit) {
            if (this.model.get('_accessLevel') >= AccessType.ADMIN) {
                this.editGroup();
            }
            this.edit = false;
        }

        _.each($('.g-group-tabs>li>a'), (el) => {
            var tabLink = $(el);
            tabLink.tab().on('shown.bs.tab', (e) => {
                this.tab = $(e.currentTarget).attr('name');
                router.navigate('group/' + this.model.get('_id') + '/' + this.tab);
            });

            if (tabLink.attr('name') === this.tab) {
                tabLink.tab('show');
            }
        });

        return this;
    },

    _renderInvitesWidget: function () {
        new GroupInvitesWidget({
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
        confirm({
            text: 'Are you sure you want to leave this group?',
            confirmCallback: () => {
                this.model.off('g:removed').on('g:removed', () => {
                    this.render();
                }).removeMember(getCurrentUser().get('_id'));
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
            .sendInvitation(userId, AccessType.READ, true);
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
            if (userAccess.level === AccessType.WRITE) {
                mods.push(userAccess);
            } else if (userAccess.level === AccessType.ADMIN) {
                admins.push(userAccess);
            }
        }, this);

        this.adminsWidget = new GroupAdminsWidget({
            el: this.$('.g-group-admins-container'),
            group: this.model,
            admins: admins,
            parentView: this
        }).off().on('g:demoteUser', function (userId) {
            this.model.off('g:demoted').on('g:demoted', this.render, this)
                .demoteUser(userId, AccessType.ADMIN);
        }, this).on('g:removeMember', this.removeMember, this)
            .on('g:moderatorAdded', this.render, this)
            .render();

        this.modsWidget = new GroupModsWidget({
            el: this.$('.g-group-mods-container'),
            group: this.model,
            moderators: mods,
            parentView: this
        }).on('g:demoteUser', function (userId) {
            this.model.off('g:demoted').on('g:demoted', this.render, this)
                .demoteUser(userId, AccessType.WRITE);
        }, this).on('g:removeMember', this.removeMember, this)
            .on('g:adminAdded', this.render, this)
            .render();

        this.membersWidget = new GroupMembersWidget({
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
                events.trigger('g:alert', {
                    text: err.responseJSON.message,
                    type: 'warning'
                });
            }, this).sendInvitation(params.user.id, params.level, false, opts);
        }, this).on('g:removeMember', this.removeMember, this)
            .on('g:moderatorAdded', this.render, this)
            .on('g:adminAdded', this.render, this);
    }
}, {
    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    fetchAndInit: function (groupId, params) {
        var group = new GroupModel();
        group.set({ _id: groupId }).once('g:fetched', function () {
            events.trigger('g:navigateTo', GroupView, _.extend({
                group: group
            }, params || {}));
        }, this).fetch();
    }
});

export default GroupView;
