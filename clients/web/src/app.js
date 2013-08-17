girder.App = Backbone.View.extend({
    el: 'body',

    initialize: function (settings) {
        this.render();

        new girder.views.LayoutGlobalNavView({
            el: this.$('#g-global-nav-container')
        }).render().on('navigateTo', function (goto) {
            console.log('should navigate to ' + goto); // TODO
        }, this);

        new girder.views.LayoutHeaderView({
            el: this.$('#g-app-header-container')
        }).render();

        new girder.views.LayoutFooterView({
            el: this.$('#g-app-footer-container')
        }).render();

        Backbone.history.start({
            pushState: false,
            root: settings.root
        });
    },

    render: function () {
        this.$el.html(jade.templates.layout());
        return this;
    }
});
