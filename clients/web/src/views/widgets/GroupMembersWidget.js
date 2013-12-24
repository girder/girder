/**
 * This view shows a list of members of a group.
 */
girder.views.GroupMembersWidget = Backbone.View.extend({
    events: {
        'click a.g-member-name': function (e) {
            girder.events.trigger('g:navigateTo', girder.views.UserView, {
                id: $(e.currentTarget).parents('li').attr('userid')
            });
        },

        'click a.g-group-member-remove': function (e) {

        }
    },

    initialize: function (settings) {
        this.model = settings.group;
        this.membersColl = new girder.collections.UserCollection();
        this.membersColl.altUrl =
            'group/' + this.model.get('_id') + '/member';
        this.membersColl.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    render: function () {
        this.$el.html(jade.templates.groupMemberList({
            group: this.model,
            members: this.membersColl.models,
            level: this.model.get('_accessLevel'),
            accessType: girder.AccessType
        }));

        new girder.views.PaginateWidget({
            el: this.$('.g-member-pagination'),
            collection: this.membersColl
        }).render();

        this.$('.g-group-member-remove,.g-group-member-promote').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }
});
