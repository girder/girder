/**
 * This view shows a list of pending invitations to the group.
 */
girder.views.GroupInvitesWidget = Backbone.View.extend({
    events: {
        'click .g-group-admin-demote': function (e) {
            var li = $(e.currentTarget).parents('li');
            var view = this;

            girder.confirm({
                text: 'Are you sure you want to remove admin privileges ' +
                    'from <b>' + li.attr('username') + '</b>?',
                confirmCallback: function () {
                    view.trigger('g:demoteUser', li.attr('userid'));
                }
            });
        },

        'click a.g-member-name': function (e) {
            girder.events.trigger('g:navigateTo', girder.views.UserView, {
                id: $(e.currentTarget).parents('li').attr('userid')
            });
        }
    },

    initialize: function (settings) {
        this.collection = settings.invitees;
        this.group = settings.group;
    },

    render: function () {
        this.$el.html(jade.templates.groupInviteList({
            level: this.group.get('_accessLevel'),
            invitees: this.collection.models,
            accessType: girder.AccessType
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
