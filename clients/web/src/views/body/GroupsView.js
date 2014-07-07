/**
 * This view lists groups.
 */
girder.views.GroupsView = girder.View.extend({
    events: {
        'click a.g-group-link': function (event) {
            var cid = $(event.currentTarget).attr('g-group-cid');
            girder.router.navigate('group/' + this.collection.get(cid).id, {trigger: true});
        },
        'submit .g-group-search-form': function (event) {
            event.preventDefault();
        },
        'click .g-group-create-button': function () {
            this.createGroupDialog();
        }
    },

    initialize: function (settings) {
        this.collection = new girder.collections.GroupCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    render: function () {
        this.$el.html(jade.templates.groupList({
            groups: this.collection.models,
            girder: girder
        }));

        new girder.views.PaginateWidget({
            el: this.$('.g-group-pagination'),
            collection: this.collection
        }).render();

        new girder.views.SearchFieldWidget({
            el: this.$('.g-groups-search-container'),
            placeholder: 'Search groups...',
            types: ['group']
        }).off().on('g:resultClicked', this._gotoGroup, this).render();

        return this;
    },

    /**
     * Prompt the user to create a new group
     */
    createGroupDialog: function () {
        new girder.views.EditGroupWidget({
            el: $('#g-dialog-container')
        }).off('g:saved').on('g:saved', function (group) {
            // Since the user has now joined this group, we can append its ID
            // to their groups list
            var userGroups = girder.currentUser.get('groups') || [];
            userGroups.push(group.get('_id'));
            girder.currentUser.set('groups', userGroups);

            girder.router.navigate('group/' + group.get('_id'), {trigger: true});

        }, this).render();
    },

    /**
     * When the user clicks a search result group, this helper method
     * will navigate them to the view for that group.
     */
    _gotoGroup: function (result) {
        var group = new girder.models.GroupModel();
        group.set('_id', result.id).on('g:fetched', function () {
            girder.router.navigate('group/' + group._id, {trigger: true});
        }, this).fetch();
    }

});

girder.router.route('groups', 'groups', function () {
    girder.events.trigger('g:navigateTo', girder.views.GroupsView);
    girder.events.trigger('g:highlightItem', 'GroupsView');
});
