var girder            = require('girder/init');
var Auth              = require('girder/auth');
var Events            = require('girder/events');
var GroupCollection   = require('girder/collections/GroupCollection');
var GroupModel        = require('girder/models/GroupModel');
var View              = require('girder/view');
var PaginateWidget    = require('girder/views/widgets/PaginateWidget');
var SearchFieldWidget = require('girder/views/widgets/SearchFieldWidget');
var EditGroupWidget   = require('girder/views/widgets/EditGroupWidget');
var MiscFunctions     = require('girder/utilities/MiscFunctions');

/**
 * This view lists groups.
 */
var GroupsView = View.extend({
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
        MiscFunctions.cancelRestRequests('fetch');
        this.collection = new GroupCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.paginateWidget = PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.searchWidget = SearchFieldWidget({
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
        new EditGroupWidget({
            el: $('#g-dialog-container'),
            parentView: this
        }).off('g:saved').on('g:saved', function (group) {
            // Since the user has now joined this group, we can append its ID
            // to their groups list
            var userGroups = Auth.getCurrentUser().get('groups') || [];
            userGroups.push(group.get('_id'));
            Auth.getCurrentUser().set('groups', userGroups);

            girder.router.navigate('group/' + group.get('_id'), {trigger: true});
        }, this).render();
    },

    /**
     * When the user clicks a search result group, this helper method
     * will navigate them to the view for that group.
     */
    _gotoGroup: function (result) {
        var group = new GroupModel();
        group.set('_id', result.id).on('g:fetched', function () {
            girder.router.navigate('group/' + group.get('_id'), {trigger: true});
        }, this).fetch();
    }

});

module.exports = GroupsView;

girder.router.route('groups', 'groups', function (params) {
    Events.trigger('g:navigateTo', GroupsView, params || {});
    Events.trigger('g:highlightItem', 'GroupsView');
});
