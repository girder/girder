import $ from 'jquery';

import CollectionCollection from 'girder/collections/CollectionCollection';
import CollectionModel from 'girder/models/CollectionModel';
import EditCollectionWidget from 'girder/views/widgets/EditCollectionWidget';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import router from 'girder/router';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import View from 'girder/views/View';
import { cancelRestRequests } from 'girder/rest';
import { formatDate, formatSize, renderMarkdown, DATE_MINUTE } from 'girder/misc';
import { getCurrentUser } from 'girder/auth';

import CollectionListTemplate from 'girder/templates/body/collectionList.pug';

import 'girder/stylesheets/body/collectionList.styl';

/**
 * This view lists the collections.
 */
var CollectionsView = View.extend({
    events: {
        'click a.g-collection-link': function (event) {
            var cid = $(event.currentTarget).attr('g-collection-cid');
            router.navigate('collection/' + this.collection.get(cid).id, {trigger: true});
        },
        'click button.g-collection-create-button': 'createCollectionDialog',
        'submit .g-collections-search-form': function (event) {
            event.preventDefault();
        },
        'click .g-show-description': '_toggleDescription'
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.collection = new CollectionCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Search collections...',
            types: ['collection'],
            parentView: this
        }).on('g:resultClicked', this._gotoCollection, this);

        this.create = settings.dialog === 'create';
    },

    /**
     * Prompt the user to create a new collection
     */
    createCollectionDialog: function () {
        var container = $('#g-dialog-container');

        new EditCollectionWidget({
            el: container,
            parentView: this
        }).on('g:saved', function (collection) {
            router.navigate('collection/' + collection.get('_id'),
                                   {trigger: true});
        }, this).render();
    },

    render: function () {
        this.$el.html(CollectionListTemplate({
            collections: this.collection.toArray(),
            getCurrentUser: getCurrentUser,
            formatDate: formatDate,
            DATE_MINUTE: DATE_MINUTE,
            formatSize: formatSize
        }));

        this.paginateWidget.setElement(this.$('.g-collection-pagination')).render();
        this.searchWidget.setElement(this.$('.g-collections-search-container')).render();

        if (this.create) {
            this.createCollectionDialog();
        }

        return this;
    },

    /**
     * When the user clicks a search result collection, this helper method
     * will navigate them to the view for that specific collection.
     */
    _gotoCollection: function (result) {
        var collection = new CollectionModel();
        collection.set('_id', result.id).on('g:fetched', function () {
            router.navigate('/collection/' + collection.get('_id'), {trigger: true});
        }, this).fetch();
    },

    _toggleDescription: function (e) {
        const link = $(e.currentTarget);
        const cid = link.attr('cid');
        const dest = this.$(`.g-collection-description[cid="${cid}"]`);

        if (link.attr('state') === 'hidden') {
            renderMarkdown(this.collection.get(cid).get('description'), dest);
            dest.removeClass('hide');
            link.attr('state', 'visible');
            link.find('i').removeClass('icon-down-dir').addClass('icon-up-dir');
            link.find('span').text('Hide description');
        } else {
            dest.addClass('hide');
            link.attr('state', 'hidden');
            link.find('i').removeClass('icon-up-dir').addClass('icon-down-dir');
            link.find('span').text('Show description');
        }
    }
});

export default CollectionsView;
