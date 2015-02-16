/**
 * This view shows a list of moderators of a group.
 */
girder.views.GroupModsWidget = girder.View.extend({
    events: {
        'click .g-group-mod-promote': function (e) {
            var userid = $(e.currentTarget).parents('li').attr('userid');
            var user = new girder.models.UserModel({_id: userid});
            this.model.off('g:promoted').on('g:promoted', function () {
                this.trigger('g:adminAdded');
            }, this).promoteUser(user, girder.AccessType.ADMIN);
        },

        'click .g-group-mod-demote': function (e) {
            var li = $(e.currentTarget).parents('li');
            var view = this;

            girder.confirm({
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

            girder.confirm({
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
        this.$el.html(girder.templates.groupModList({
            group: this.model,
            level: this.model.get('_accessLevel'),
            moderators: this.moderators,
            accessType: girder.AccessType
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
