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
        girder.cancelRestRequests('fetch');
        this.collection = new girder.collections.GroupCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.paginateWidget = new girder.views.PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.searchWidget = new girder.views.SearchFieldWidget({
            placeholder: 'Search groups...',
            types: ['group'],
            parentView: this
        }).on('g:resultClicked', this._gotoGroup, this);

        this.create = settings.dialog === 'create';
    },

    render: function () {
        this.$el.html(girder.templates.groupList({
            groups: this.collection.toArray(),
            girder: girder
        }));

        this.paginateWidget.setElement(this.$('.g-group-pagination')).render();
        this.searchWidget.setElement(this.$('.g-groups-search-container')).render();

        if (this.create) {
            this.createGroupDialog();
            this.create = false;
        }

        return this;
    },

    /**
     * Prompt the user to create a new group
     */
    createGroupDialog: function () {
        new girder.views.EditGroupWidget({
            el: $('#g-dialog-container'),
            parentView: this
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
            girder.router.navigate('group/' + group.get('_id'), {trigger: true});
        }, this).fetch();
    }

});

girder.router.route('groups', 'groups', function (params) {
    girder.events.trigger('g:navigateTo', girder.views.GroupsView, params || {});
    girder.events.trigger('g:highlightItem', 'GroupsView');
});
