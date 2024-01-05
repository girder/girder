import OAuthLoginView from './OAuthLoginView';

const RegisterView = girder.views.layout.RegisterView;
const { getCurrentUser } = girder.auth;
const { wrap } = girder.utilities.PluginUtils;

/**
 * We want to add some additional stuff to the login view when it is shown.
 */
wrap(RegisterView, 'render', function (render) {
    render.call(this);

    if (!getCurrentUser()) {
        new OAuthLoginView({
            el: this.$('.modal-body'),
            parentView: this,
            modeText: 'register automatically'
        }).render();
    }

    return this;
});
