import LoginView from 'girder/views/layout/LoginView';
import { wrap } from 'girder/utilities/PluginUtils';

import OAuthLoginView from './OAuthLoginView';

wrap(LoginView, 'render', function (render) {
    render.call(this);
    new OAuthLoginView({
        el: this.$('.modal-body'),
        parentView: this
    }).render();
    return this;
});
