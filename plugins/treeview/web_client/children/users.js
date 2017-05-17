import _ from 'underscore';

import request from '../request';
import getCurrentUser from '../auth';
import { user } from '../types';

export default function () {
    return request({
        path: 'user'
    }).then((users) => {
        const current = getCurrentUser() || {};
        return _.map(
            _.reject(users, {_id: current._id}),
            user
        );
    });
}
