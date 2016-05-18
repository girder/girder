var $                    = require('jquery');
var girder               = require('girder/init');
var Events               = require('girder/events');
var CollectionCollection = require('girder/collections/CollectionCollection');
var CollectionModel      = require('girder/models/CollectionModel');
var View                 = require('girder/view');
var PaginateWidget       = require('girder/views/widgets/PaginateWidget');
var SearchFieldWidget    = require('girder/views/widgets/SearchFieldWidget');
var EditCollectionWidget = require('girder/views/widgets/EditCollectionWidget');
var Rest                 = require('girder/utilities/Rest');

var CollectionListTemplate = require('girder/templates/body/collectionList.jade');

/**
 * This view lists the collections.
 */
var CollectionsView = View.extend({
    events: {
        'click a.g-collection-link': function (event) {
            var cid = $(event.currentTarget).attr('g-collection-cid');
            girder.router.navigate('collection/' + this.collection.get(cid).id, {trigger: true});
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
            girder.router.navigate('collection/' + collection.get('_id'),
                                   {trigger: true});
        }, this).render();
    },

    render: function () {
        this.$el.html(CollectionListTemplate({
            collections: this.collection.toArray(),
            girder: girder
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
            girder.router.navigate('/collection/' + collection.get('_id'), {trigger: true});
        }, this).fetch();
    }
});

module.exports = CollectionsView;

girder.router.route('collections', 'collections', function (params) {
    Events.trigger('g:navigateTo', CollectionsView, params || {});
    Events.trigger('g:highlightItem', 'CollectionsView');
});
