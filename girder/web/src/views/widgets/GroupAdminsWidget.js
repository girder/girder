import $ from 'jquery';
import _ from 'underscore';

import UserModel from '@girder/core/models/UserModel';
import UserView from '@girder/core/views/body/UserView';
import View from '@girder/core/views/View';
import { AccessType } from '@girder/core/constants';
import { confirm } from '@girder/core/dialog';
import events from '@girder/core/events';

import GroupAdminListTemplate from '@girder/core/templates/widgets/groupAdminList.pug';

import 'bootstrap/js/dropdown';

/**
 * This view shows a list of administrators of a group.
 */
var GroupAdminsWidget = View.extend({
    events: {
        'click .g-demote-moderator': function (e) {
            var li = $(e.currentTarget).parents('.g-group-admins>li');
            var userid = li.attr('userid');

            confirm({
                text: 'Are you sure you want to demote <b>' +
                    _.escape(li.attr('username')) + '</b> to a moderator?',
                escapedHtml: true,
                confirmCallback: () => {
                    var user = new UserModel({ _id: userid });
                    this.model.off('g:promoted').on('g:promoted', () => {
                        this.trigger('g:moderatorAdded');
                    }, this).promoteUser(user, AccessType.WRITE);
                }
            });
        },

        'click .g-demote-member': function (e) {
            var li = $(e.currentTarget).parents('.g-group-admins>li');

            confirm({
                text: 'Are you sure you want to remove admin privileges ' +
                    'from <b>' + _.escape(li.attr('username')) + '</b>?',
                escapedHtml: true,
                confirmCallback: () => {
                    this.trigger('g:demoteUser', li.attr('userid'));
                }
            });
        },

        'click a.g-group-admin-remove': function (e) {
            var li = $(e.currentTarget).parents('li');

            confirm({
                text: 'Are you sure you want to remove <b> ' +
                    _.escape(li.attr('username')) +
                    '</b> from this group?',
                escapedHtml: true,
                confirmCallback: () => {
                    this.trigger('g:removeMember', li.attr('userid'));
                }
            });
        },

        'click a.g-member-name': function (e) {
            events.trigger('g:navigateTo', UserView, {
                id: $(e.currentTarget).parents('li').attr('userid')
            });
        }
    },

    initialize: function (settings) {
        this.model = settings.group;
        this.admins = settings.admins;
    },

    render: function () {
        this.$el.html(GroupAdminListTemplate({
            group: this.model,
            level: this.model.get('_accessLevel'),
            admins: this.admins,
            accessType: AccessType
        }));

        return this;
    }
});

export default GroupAdminsWidget;
