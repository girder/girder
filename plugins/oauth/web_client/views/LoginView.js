import LoginView from 'girder/views/layout/LoginView';
import { wrap } from 'girder/utilities/PluginUtils';

import OAuthLoginView from './OAuthLoginView';

wrap(LoginView, 'render', function (render) {
    render.call(this);
    new OAuthLoginView({
        el: this.$('.modal-body'),
        parentView: this,
        enablePasswordLogin: this.enablePasswordLogin
    }).render();
    return this;
});
