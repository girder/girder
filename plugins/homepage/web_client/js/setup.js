girder.exposePluginConfig('homepage', 'plugins/homepage/config');

girder.wrap(girder.views.FrontPageView, 'render', function (render) {
    girder.restRequest({
        type: 'GET',
        path: 'homepage/markdown'
    }).done(_.bind(function (resp) {
        this.$el.html(girder.renderMarkdown(resp['homepage.markdown']));
    }, this));

    return this;
});
