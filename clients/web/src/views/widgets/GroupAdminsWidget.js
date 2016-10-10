import $ from 'jquery';
import _ from 'underscore';

import UserModel from 'girder/models/UserModel';
import UserView from 'girder/views/body/UserView';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { confirm } from 'girder/dialog';
import events from 'girder/events';

import GroupAdminListTemplate from 'girder/templates/widgets/groupAdminList.pug';

import 'bootstrap/js/dropdown';
import 'bootstrap/js/tooltip';

/**
 * This view shows a list of administrators of a group.
 */
var GroupAdminsWidget = View.extend({
    events: {
        'click .g-demote-moderator': function (e) {
            var li = $(e.currentTarget).parents('.g-group-admins>li');
            var userid = li.attr('userid');
            var view = this;

            confirm({
                text: 'Are you sure you want to demote <b>' +
                    _.escape(li.attr('username')) + '</b> to a moderator?',
                escapedHtml: true,
                confirmCallback: function () {
                    var user = new UserModel({_id: userid});
                    view.model.off('g:promoted').on('g:promoted', function () {
                        this.trigger('g:moderatorAdded');
                    }, view).promoteUser(user, AccessType.WRITE);
                }
            });
        },

        'click .g-demote-member': function (e) {
            var li = $(e.currentTarget).parents('.g-group-admins>li');
            var view = this;

            confirm({
                text: 'Are you sure you want to remove admin privileges ' +
                    'from <b>' + _.escape(li.attr('username')) + '</b>?',
                escapedHtml: true,
                confirmCallback: function () {
                    view.trigger('g:demoteUser', li.attr('userid'));
                }
            });
        },

        'click a.g-group-admin-remove': function (e) {
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
        this.admins = settings.admins;
    },

    render: function () {
        this.$el.html(GroupAdminListTemplate({
            group: this.model,
            level: this.model.get('_accessLevel'),
            admins: this.admins,
            accessType: AccessType
        }));

        this.$('.g-group-admin-demote').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }
});

export default GroupAdminsWidget;
