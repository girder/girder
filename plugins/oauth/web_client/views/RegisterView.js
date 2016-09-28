import RegisterView from 'girder/views/layout/RegisterView';
import { getCurrentUser } from 'girder/auth';
import { wrap } from 'girder/utilities/PluginUtils';

import OAuthLoginView from './OAuthLoginView';

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
