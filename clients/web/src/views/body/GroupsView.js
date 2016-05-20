var $                 = require('jquery');

var Auth              = require('girder/auth');
var EditGroupWidget   = require('girder/views/widgets/EditGroupWidget');
var Events            = require('girder/events');
var GroupCollection   = require('girder/collections/GroupCollection');
var GroupListTemplate = require('girder/templates/body/groupList.jade');
var GroupModel        = require('girder/models/GroupModel');
var MiscFunctions     = require('girder/utilities/MiscFunctions');
var PaginateWidget    = require('girder/views/widgets/PaginateWidget');
var Rest              = require('girder/rest');
var Router            = require('girder/router');
var SearchFieldWidget = require('girder/views/widgets/SearchFieldWidget');
var View              = require('girder/view');

/**
 * This view lists groups.
 */
var GroupsView = View.extend({
    events: {
        'click a.g-group-link': function (event) {
            var cid = $(event.currentTarget).attr('g-group-cid');
            Router.navigate('group/' + this.collection.get(cid).id, {trigger: true});
        },
        'submit .g-group-search-form': function (event) {
            event.preventDefault();
        },
        'click .g-group-create-button': function () {
            this.createGroupDialog();
        }
    },

    initialize: function (settings) {
        Rest.cancelRestRequests('fetch');
        this.collection = new GroupCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Search groups...',
            types: ['group'],
            parentView: this
        }).on('g:resultClicked', this._gotoGroup, this);

        this.create = settings.dialog === 'create';
    },

    render: function () {
        this.$el.html(GroupListTemplate({
            groups: this.collection.toArray(),
            Auth: Auth,
            MiscFunctions: MiscFunctions
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

            Router.navigate('group/' + group.get('_id'), {trigger: true});
        }, this).render();
    },

    /**
     * When the user clicks a search result group, this helper method
     * will navigate them to the view for that group.
     */
    _gotoGroup: function (result) {
        var group = new GroupModel();
        group.set('_id', result.id).on('g:fetched', function () {
            Router.navigate('group/' + group.get('_id'), {trigger: true});
        }, this).fetch();
    }

});

module.exports = GroupsView;

Router.route('groups', 'groups', function (params) {
    Events.trigger('g:navigateTo', GroupsView, params || {});
    Events.trigger('g:highlightItem', 'GroupsView');
});
