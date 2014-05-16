/**
 * This view shows a list of moderators of a group.
 */
girder.views.GroupModsWidget = girder.View.extend({
    events: {
        'click .g-group-mod-demote': function (e) {
            var li = $(e.currentTarget).parents('li');
            var view = this;

            girder.confirm({
                text: 'Are you sure you want to remove moderator privileges ' +
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
        this.moderators = settings.moderators;
    },

    render: function () {
        this.$el.html(jade.templates.groupModList({
            group: this.model,
            level: this.model.get('_accessLevel'),
            moderators: this.moderators,
            accessType: girder.AccessType
        }));

        this.$('.g-group-mod-demote').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }
});
