import _ from 'underscore';

import request from '../request';
import { folder } from '../types';

export default function (home) {
    return request({
        path: 'folder',
        data: {
            parentId: home._id,
            parentType: 'user'
        }
    }).then((folders) => {
        return _.map(folders, folder);
    });
}
