import _ from 'underscore';

import request from '../request';
import { file } from '../types';

export default function (parent) {
    return request({
        path: `item/${parent._id}/files`
    }).then((files) => {
        return _.map(files, file);
    });
}
