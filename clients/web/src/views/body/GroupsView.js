import $ from 'jquery';

import { getCurrentUser } from 'girder/auth';
import EditGroupWidget from 'girder/views/widgets/EditGroupWidget';
import { events } from 'girder/events';
import GroupCollection from 'girder/collections/GroupCollection';
import GroupListTemplate from 'girder/templates/body/groupList.jade';
import GroupModel from 'girder/models/GroupModel';
import { formatDate, DATE_DAY } from 'girder/utilities/MiscFunctions';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import { cancelRestRequests } from 'girder/rest';
import router from 'girder/router';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import View from 'girder/view';

/**
 * This view lists groups.
 */
var GroupsView = View.extend({
    events: {
        'click a.g-group-link': function (event) {
            var cid = $(event.currentTarget).attr('g-group-cid');
            router.navigate('group/' + this.collection.get(cid).id, {trigger: true});
        },
        'submit .g-group-search-form': function (event) {
            event.preventDefault();
        },
        'click .g-group-create-button': function () {
            this.createGroupDialog();
        }
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
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
            getCurrentUser: getCurrentUser,
            formatDate: formatDate,
            DATE_DAY: DATE_DAY
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
            var userGroups = getCurrentUser().get('groups') || [];
            userGroups.push(group.get('_id'));
            getCurrentUser().set('groups', userGroups);

            router.navigate('group/' + group.get('_id'), {trigger: true});
        }, this).render();
    },

    /**
     * When the user clicks a search result group, this helper method
     * will navigate them to the view for that group.
     */
    _gotoGroup: function (result) {
        var group = new GroupModel();
        group.set('_id', result.id).on('g:fetched', function () {
            router.navigate('group/' + group.get('_id'), {trigger: true});
        }, this).fetch();
    }

});

router.route('groups', 'groups', function (params) {
    events.trigger('g:navigateTo', GroupsView, params || {});
    events.trigger('g:highlightItem', 'GroupsView');
});

export default GroupsView;
