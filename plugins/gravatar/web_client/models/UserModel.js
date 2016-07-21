import UserModel from 'girder/models/UserModel';
import { apiRoot } from 'girder/rest';

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
