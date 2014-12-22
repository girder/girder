/**
 * We want to add some additional stuff to the login view when it is shown.
 */
girder.wrap(girder.views.LoginView, 'render', function (render) {
    render.call(this);
    new girder.views.oauth_LoginView({
        el: this.$('.modal-body'),
        parentView: this
    });
    return this;
});

girder.exposePluginConfig('oauth', 'plugins/oauth/config');
