import UserModel from 'girder/models/UserModel';
import { getApiRoot } from 'girder/rest';

UserModel.prototype.getGravatarUrl = function (size) {
    size = size || 64;
    var baseUrl = this.get('gravatar_baseUrl');
    if (baseUrl) {
        return baseUrl;
    } else {
        return `${getApiRoot()}/user/${this.id}/gravatar?size=${size}`;
    }
};
