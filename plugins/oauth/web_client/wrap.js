import { wrap } from 'girder/utilities/PluginUtils';
import { getCurrentUser } from 'girder/auth';

import OAuthLoginView from './views/LoginView';

/**
 * We want to add some additional stuff to the login view when it is shown.
 */
import LoginView from 'girder/views/layout/LoginView';
wrap(LoginView, 'render', function (render) {
    render.call(this);
    new OAuthLoginView({
        el: this.$('.modal-body'),
        parentView: this
    });
    return this;
});

import RegisterView from 'girder/views/layout/RegisterView';
wrap(RegisterView, 'render', function (render) {
    render.call(this);

    if (!getCurrentUser()) {
        new OAuthLoginView({
            el: this.$('.modal-body'),
            parentView: this,
            modeText: 'register automatically'
        });
    }

    return this;
});
