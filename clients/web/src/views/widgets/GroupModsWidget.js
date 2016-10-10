import $ from 'jquery';
import _ from 'underscore';

import UserModel from 'girder/models/UserModel';
import UserView from 'girder/views/body/UserView';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { confirm } from 'girder/dialog';
import events from 'girder/events';

import GroupModListTemplate from 'girder/templates/widgets/groupModList.pug';

import 'bootstrap/js/tooltip';

/**
 * This view shows a list of moderators of a group.
 */
var GroupModsWidget = View.extend({
    events: {
        'click .g-group-mod-promote': function (e) {
            var userid = $(e.currentTarget).parents('li').attr('userid');
            var user = new UserModel({_id: userid});
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:adminAdded');
            }, this).promoteUser(user, AccessType.ADMIN);
        },

        'click .g-group-mod-demote': function (e) {
            var li = $(e.currentTarget).parents('li');
            var view = this;

            confirm({
                text: 'Are you sure you want to remove moderator privileges ' +
                    'from <b>' + _.escape(li.attr('username')) + '</b>?',
                escapedHtml: true,
                confirmCallback: function () {
                    view.trigger('g:demoteUser', li.attr('userid'));
                }
            });
        },

        'click a.g-group-mod-remove': function (e) {
            var view = this;
            var li = $(e.currentTarget).parents('li');

            confirm({
                text: 'Are you sure you want to remove <b> ' +
                    _.escape(li.attr('username')) +
                    '</b> from this group?',
                escapedHtml: true,
                confirmCallback: function () {
                    view.trigger('g:removeMember', li.attr('userid'));
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

        this.$('.g-group-mod-demote.g-group-mod-promote,.g-group-mod-remove').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }
});

export default GroupModsWidget;
