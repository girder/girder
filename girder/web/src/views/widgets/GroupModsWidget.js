import $ from 'jquery';
import _ from 'underscore';

import UserModel from '@girder/core/models/UserModel';
import UserView from '@girder/core/views/body/UserView';
import View from '@girder/core/views/View';
import { AccessType } from '@girder/core/constants';
import { confirm } from '@girder/core/dialog';
import events from '@girder/core/events';

import GroupModListTemplate from '@girder/core/templates/widgets/groupModList.pug';

/**
 * This view shows a list of moderators of a group.
 */
var GroupModsWidget = View.extend({
    events: {
        'click .g-group-mod-promote': function (e) {
            var userid = $(e.currentTarget).parents('li').attr('userid');
            var user = new UserModel({ _id: userid });
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:adminAdded');
            }, this).promoteUser(user, AccessType.ADMIN);
        },

        'click .g-group-mod-demote': function (e) {
            var li = $(e.currentTarget).parents('li');

            confirm({
                text: 'Are you sure you want to remove moderator privileges ' +
                    'from <b>' + _.escape(li.attr('username')) + '</b>?',
                escapedHtml: true,
                confirmCallback: () => {
                    this.trigger('g:demoteUser', li.attr('userid'));
                }
            });
        },

        'click a.g-group-mod-remove': function (e) {
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
        this.moderators = settings.moderators;
    },

    render: function () {
        this.$el.html(GroupModListTemplate({
            group: this.model,
            level: this.model.get('_accessLevel'),
            moderators: this.moderators,
            accessType: AccessType
        }));

        return this;
    }
});

export default GroupModsWidget;
