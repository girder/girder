import router from 'girder/router';
import UserModel from 'girder/models/UserModel';
import { apiRoot } from 'girder/rest';
import { events } from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/MiscFunctions';

import ConfigView from './ConfigView';

exposePluginConfig('gravatar', 'plugins/gravatar/config');
router.route('plugins/gravatar/config', 'gravatarConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

UserModel.prototype.getGravatarUrl = function (size) {
    size = size || 64;
    var baseUrl = this.get('gravatar_baseUrl');
    if (baseUrl) {
        return baseUrl;
    } else {
        return apiRoot + '/user/' + this.get('_id') +
            '/gravatar?size=' + size;
    }
};
