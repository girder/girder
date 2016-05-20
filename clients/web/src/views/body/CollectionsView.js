var $                      = require('jquery');

var Auth                   = require('girder/auth');
var CollectionCollection   = require('girder/collections/CollectionCollection');
var CollectionListTemplate = require('girder/templates/body/collectionList.jade');
var CollectionModel        = require('girder/models/CollectionModel');
var EditCollectionWidget   = require('girder/views/widgets/EditCollectionWidget');
var Events                 = require('girder/events');
var MiscFunctions          = require('girder/utilities/MiscFunctions');
var PaginateWidget         = require('girder/views/widgets/PaginateWidget');
var Rest                   = require('girder/rest');
var Router                 = require('girder/router');
var SearchFieldWidget      = require('girder/views/widgets/SearchFieldWidget');
var View                   = require('girder/view');

/**
 * This view lists the collections.
 */
var CollectionsView = View.extend({
    events: {
        'click a.g-collection-link': function (event) {
            var cid = $(event.currentTarget).attr('g-collection-cid');
            Router.navigate('collection/' + this.collection.get(cid).id, {trigger: true});
        },
        'click button.g-collection-create-button': 'createCollectionDialog',
        'submit .g-collections-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function (settings) {
        Rest.cancelRestRequests('fetch');
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
            Router.navigate('collection/' + collection.get('_id'),
                                   {trigger: true});
        }, this).render();
    },

    render: function () {
        this.$el.html(CollectionListTemplate({
            collections: this.collection.toArray(),
            Auth: Auth,
            MiscFunctions: MiscFunctions
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
            Router.navigate('/collection/' + collection.get('_id'), {trigger: true});
        }, this).fetch();
    }
});

module.exports = CollectionsView;

Router.route('collections', 'collections', function (params) {
    Events.trigger('g:navigateTo', CollectionsView, params || {});
    Events.trigger('g:highlightItem', 'CollectionsView');
});
