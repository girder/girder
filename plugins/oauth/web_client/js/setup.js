girder.wrap(girder.views.LoginView, 'render', function (render) {
    render.call(this);
    new girder.views.oauth_LoginView({
        el: this.$('.modal-body')
    });
    return this;
});
