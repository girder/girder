import _ from 'underscore';

import request from '../utils/request';
import { folder, item } from '../types';

export default function (parent) {
    return Promise.all([
        request({
            path: 'folder',
            data: {
                parentId: parent._id,
                parentType: 'folder'
            }
        }),
        request({
            path: 'item',
            data: {
                folderId: parent._id
            }
        })
    ]).then(([folders, items]) => {
        return _.map(folders, folder)
            .concat(_.map(items, item));
    });
}
