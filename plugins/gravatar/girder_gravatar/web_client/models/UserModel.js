import UserModel from '@girder/core/models/UserModel';
import { getApiRoot } from '@girder/core/rest';

UserModel.prototype.getGravatarUrl = function (size) {
    size = size || 64;
    var baseUrl = this.get('gravatar_baseUrl');
    if (baseUrl) {
        return baseUrl;
    } else {
        return `${getApiRoot()}/user/${this.id}/gravatar?size=${size}`;
    }
};
