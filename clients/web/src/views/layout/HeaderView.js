/**
 * This view shows the header in the layout.
 */
girder.views.LayoutHeaderView = girder.View.extend({
    events: {
        'click .g-app-title': function (event) {
            girder.router.navigate('', {trigger: true});
        }
    },

    render: function () {
        this.$el.html(jade.templates.layoutHeader());

        new girder.views.LayoutHeaderUserView({
            el: this.$('.g-current-user-wrapper')
        }).render();

        this.searchWidget = new girder.views.SearchFieldWidget({
            el: this.$('.g-quick-search-container'),
            placeholder: 'Quick Search...',
            types: ['item', 'folder', 'group', 'collection', 'user']
        }).off().on('g:resultClicked', function (result) {
            this.searchWidget.resetState();
            girder.router.navigate(result.type + '/' + result.id, {
                trigger: true
            });
        }, this).render();

    }
});
