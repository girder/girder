var _             = require('underscore');
var girder        = require('girder/init');
var Constants     = require('girder/constants');
var View          = require('girder/view');
var MiscFunctions = require('girder/utilities/MiscFunctions');

/**
 * This view shows a list of pending invitations to the group.
 */
var GroupInvitesWidget = View.extend({
    events: {
        'click .g-group-uninvite': function (e) {
            var li = $(e.currentTarget).parents('li');
            var view = this;

            MiscFunctions.confirm({
                text: 'Are you sure you want to remove the invitation ' +
                    'for <b>' + _.escape(li.attr('username')) + '</b>?',
                escapedHtml: true,
                confirmCallback: function () {
                    var user = view.collection.get(li.attr('cid'));
                    view.group.off('g:removed').on('g:removed', function () {
                        view.collection.remove(user);
                        view.render();
                        view.parentView.render();
                    }).removeMember(user.get('_id'));
                }
            });
        },

        'click a.g-member-name': function (e) {
            var user = this.collection.get($(e.currentTarget).parents('li').attr('cid'));
            girder.router.navigate('user/' + user.get('_id'), {trigger: true});
        }
    },

    initialize: function (settings) {
        this.collection = settings.invitees;
        this.group = settings.group;
    },

    render: function () {
        this.$el.html(girder.templates.groupInviteList({
            level: this.group.get('_accessLevel'),
            invitees: this.collection.toArray(),
            accessType: Constants.AccessType
        }));

        this.$('a[title]').tooltip({
            container: this.$el,
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }
});

module.exports = GroupInvitesWidget;
