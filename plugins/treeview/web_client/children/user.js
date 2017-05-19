import _ from 'underscore';

import request from '../utils/request';
import { folder } from '../types';

export default function (parent) {
    return request({
        path: 'folder',
        data: {
            parentId: parent._id,
            parentType: 'user'
        }
    }).then((folders) => {
        return _.map(folders, folder);
    });
}
