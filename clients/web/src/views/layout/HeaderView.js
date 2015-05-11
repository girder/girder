/**
 * This view shows the header in the layout.
 */
girder.views.LayoutHeaderView = girder.View.extend({
    events: {
        'click .g-app-title': function () {
            girder.router.navigate('', {trigger: true});
        }
    },

    initialize: function () {
        this.userView = new girder.views.LayoutHeaderUserView({
            parentView: this
        });

        this.searchWidget = new girder.views.SearchFieldWidget({
            placeholder: 'Quick search...',
            types: ['item', 'folder', 'group', 'collection', 'user'],
            parentView: this
        }).on('g:resultClicked', function (result) {
            this.searchWidget.resetState();
            girder.router.navigate(result.type + '/' + result.id, {
                trigger: true
            });
        }, this);
    },

    render: function () {
        this.$el.html(girder.templates.layoutHeader());

        this.userView.setElement(this.$('.g-current-user-wrapper')).render();
        this.searchWidget.setElement(this.$('.g-quick-search-container')).render();
    }
});
