/**
 * This view shows a list of administrators of a group.
 */
girder.views.GroupAdminsWidget = girder.View.extend({
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
        this.model = settings.group;
        this.admins = settings.admins;
    },

    render: function () {
        this.$el.html(jade.templates.groupAdminList({
            group: this.model,
            level: this.model.get('_accessLevel'),
            admins: this.admins,
            accessType: girder.AccessType
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
