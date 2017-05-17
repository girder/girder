import _ from 'underscore';

import request from '../request';
import { folder } from '../types';

export default function (parent) {
    return request({
        path: 'folder',
        data: {
            parentId: parent._id,
            parentType: 'collection'
        }
    }).then((folders) => {
        return _.map(folders, folder);
    });
}
