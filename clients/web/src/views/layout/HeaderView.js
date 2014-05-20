/**
 * This view shows the header in the layout.
 */
girder.views.LayoutHeaderView = girder.View.extend({
    events: {
        'submit .g-item-search-form': function (event) {
            event.preventDefault();
        }
    },

    searchWidget: {},

    render: function () {
        this.$el.html(jade.templates.layoutHeader());

        new girder.views.LayoutHeaderUserView({
            el: this.$('.g-current-user-wrapper')
        }).render();

        this.searchWidget = new girder.views.SearchFieldWidget({
            el: this.$('.g-quick-search-container'),
            placeholder: 'Quick Search...',
            types: ['item']
        }).off().on('g:resultClicked', this._gotoItem, this).render();

    },

    /**
     * When the user clicks a search result item, this helper method
     * will navigate them to the view for that specific item.
     */
    _gotoItem: function (result) {
        var item = new girder.models.ItemModel();
        item.set('_id', result.id).on('g:fetched', function () {
            this.searchWidget.resetState();
            girder.router.navigate('item/' + item.get('_id'), {trigger: true});
        }, this).fetch();

        return this;
    }
});
