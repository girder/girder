import _ from 'underscore';

import { request, auth } from '../utils';
import { user } from '../types';

export default function () {
    return request({
        path: 'user'
    }).then((users) => {
        const current = auth() || {};
        return _.map(
            _.reject(users, {_id: current._id}),
            user
        );
    });
}
