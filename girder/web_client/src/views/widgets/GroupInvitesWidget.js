import $ from 'jquery';
import _ from 'underscore';

import router from '@girder/core/router';
import View from '@girder/core/views/View';
import { AccessType } from '@girder/core/constants';
import { confirm } from '@girder/core/dialog';

import GroupInviteListTemplate from '@girder/core/templates/widgets/groupInviteList.pug';

/**
 * This view shows a list of pending invitations to the group.
 */
var GroupInvitesWidget = View.extend({
    events: {
        'click .g-group-uninvite': function (e) {
            var li = $(e.currentTarget).parents('li');

            confirm({
                text: 'Are you sure you want to remove the invitation ' +
                    'for <b>' + _.escape(li.attr('username')) + '</b>?',
                escapedHtml: true,
                confirmCallback: () => {
                    var user = this.collection.get(li.attr('cid'));
                    this.group.off('g:removed').on('g:removed', () => {
                        this.collection.remove(user);
                        this.render();
                        this.parentView.render();
                    }).removeMember(user.get('_id'));
                }
            });
        },

        'click a.g-member-name': function (e) {
            var user = this.collection.get($(e.currentTarget).parents('li').attr('cid'));
            router.navigate('user/' + user.get('_id'), {trigger: true});
        }
    },

    initialize: function (settings) {
        this.collection = settings.invitees;
        this.group = settings.group;
    },

    render: function () {
        this.$el.html(GroupInviteListTemplate({
            level: this.group.get('_accessLevel'),
            invitees: this.collection.toArray(),
            accessType: AccessType
        }));

        return this;
    }
});

export default GroupInvitesWidget;
