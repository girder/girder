import OAuthLoginView from './OAuthLoginView';

const LoginView = girder.views.layout.LoginView;
const { wrap } = girder.utilities.PluginUtils;

wrap(LoginView, 'render', function (render) {
    render.call(this);
    new OAuthLoginView({
        el: this.$('.modal-body'),
        parentView: this,
        enablePasswordLogin: this.enablePasswordLogin
    }).render();
    return this;
});
